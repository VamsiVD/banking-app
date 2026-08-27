import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, isForbidden } from './api/client.js'
import './AdminHome.css'

const STATUSES = ['active', 'inactive', 'frozen', 'closed']

/**
 * Money crosses the wire as a JSON *string*, because the API models it as a
 * Decimal and floats cannot hold 0.10 exactly. Keep it a string all the way to
 * the screen — parsing to a Number to format it puts the rounding error back.
 */
function formatMoney(amount) {
  const [whole, fraction = ''] = String(amount).split('.')
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return `${grouped}.${fraction.padEnd(2, '0').slice(0, 2)}`
}

/** A balance in whole minor units (cents), so sums never touch a float. */
function minorUnits(balance) {
  const [whole, fraction = ''] = String(balance).split('.')
  return Number(whole) * 100 + Number(fraction.padEnd(2, '0').slice(0, 2))
}

function formatMinorUnits(minor) {
  const sign = minor < 0 ? '-' : ''
  const abs = Math.abs(minor)
  return `${sign}${formatMoney(`${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, '0')}`)}`
}

function AdminHome({ admin, onSignOut }) {
  const [accounts, setAccounts] = useState([])
  const [users, setUsers] = useState([])
  const [transfers, setTransfers] = useState([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [busyAccount, setBusyAccount] = useState(null)

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [sortBy, setSortBy] = useState('account_number')

  /** The three reads the page needs. Independent, so let them overlap. */
  const fetchDashboard = useCallback(
    () =>
      Promise.all([
        api.get('/accounts/'),
        api.get('/auth/users'),
        api.get('/transfers?limit=10'),
      ]),
    [],
  )

  const apply = useCallback(([accountList, userList, transferPage]) => {
    setAccounts(accountList)
    setUsers(userList)
    setTransfers(transferPage.items ?? [])
  }, [])

  // The Refresh button. Free to set state synchronously — it is an event
  // handler, not an effect.
  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      apply(await fetchDashboard())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [apply, fetchDashboard])

  // The first load. `loading` already starts true, so nothing is set until the
  // requests come back — and `cancelled` keeps a slow response from writing to
  // a component that has since gone away (StrictMode mounts twice in dev).
  useEffect(() => {
    let cancelled = false

    fetchDashboard().then(
      (data) => {
        if (cancelled) return
        apply(data)
        setLoading(false)
      },
      (err) => {
        if (cancelled) return
        setError(err.message)
        setLoading(false)
      },
    )

    return () => {
      cancelled = true
    }
  }, [apply, fetchDashboard])

  const visibleAccounts = useMemo(() => {
    const needle = search.trim().toLowerCase()
    const filtered = accounts.filter((account) => {
      if (statusFilter !== 'all' && account.status !== statusFilter) return false
      if (!needle) return true
      return (
        account.account_number.toLowerCase().includes(needle) ||
        account.account_holder_name.toLowerCase().includes(needle) ||
        account.owner_id.toLowerCase().includes(needle)
      )
    })

    return [...filtered].sort((a, b) => {
      if (sortBy === 'balance') {
        // Descending, and compared in minor units so "9.00" does not beat "10.00".
        return minorUnits(b.balance) - minorUnits(a.balance)
      }
      return String(a[sortBy]).localeCompare(String(b[sortBy]))
    })
  }, [accounts, search, statusFilter, sortBy])

  // Grouped by currency: adding USD to EUR would produce a number that means
  // nothing, so the tile shows one line per currency instead of one total.
  const balancesByCurrency = useMemo(() => {
    const groups = new Map()
    for (const account of accounts) {
      groups.set(account.currency, (groups.get(account.currency) ?? 0) + minorUnits(account.balance))
    }
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [accounts])

  const statusCounts = useMemo(() => {
    const counts = Object.fromEntries(STATUSES.map((s) => [s, 0]))
    for (const account of accounts) counts[account.status] = (counts[account.status] ?? 0) + 1
    return counts
  }, [accounts])

  async function changeStatus(account, status) {
    setBusyAccount(account.account_number)
    setError(null)
    setNotice(null)
    try {
      const updated = await api.patch(`/accounts/${account.account_number}`, { status })
      setAccounts((current) =>
        current.map((a) => (a.account_number === updated.account_number ? updated : a)),
      )
      setNotice(`Account ${updated.account_number} is now ${updated.status}.`)
    } catch (err) {
      setError(
        isForbidden(err)
          ? 'Only an administrator can change an account’s status.'
          : err.message,
      )
    } finally {
      setBusyAccount(null)
    }
  }

  async function remove(account) {
    setBusyAccount(account.account_number)
    setError(null)
    setNotice(null)
    try {
      await api.delete(`/accounts/${account.account_number}`)
      setAccounts((current) =>
        current.filter((a) => a.account_number !== account.account_number),
      )
      setNotice(`Account ${account.account_number} deleted.`)
    } catch (err) {
      // The expected refusal, not a bug: an account that has moved money keeps
      // its ledger entries, so it is closed rather than deleted.
      setError(
        err.code === 'account_has_history'
          ? `Account ${account.account_number} has transaction history and cannot be deleted. Set its status to “closed” instead.`
          : err.message,
      )
    } finally {
      setBusyAccount(null)
    }
  }

  return (
    <main className="admin-home">
      <header className="top-bar">
        <div>
          <h1>Banks-<span style={{ display: 'inline-block', transform: 'scaleX(-1)' }}>R</span>-Us</h1>
          <p>Administrator console</p>
        </div>

        <div className="top-bar-actions">
          <span className="who">{admin?.email}</span>
          <button type="button" onClick={onSignOut}>
            Sign Out
          </button>
        </div>
      </header>

      <div className="page-content">
        {error && (
          <p className="banner banner-error" role="alert">
            {error}
          </p>
        )}
        {notice && (
          <p className="banner banner-notice" role="status">
            {notice}
          </p>
        )}

        <section className="summary">
          <h2>Overview</h2>

          <div className="tiles">
            <div className="tile">
              <span className="tile-label">Accounts</span>
              <strong className="tile-value">{accounts.length}</strong>
            </div>

            <div className="tile">
              <span className="tile-label">Registered customers</span>
              <strong className="tile-value">{users.length}</strong>
            </div>

            <div className="tile">
              <span className="tile-label">Total held</span>
              {balancesByCurrency.length === 0 ? (
                <strong className="tile-value">—</strong>
              ) : (
                balancesByCurrency.map(([currency, minor]) => (
                  <strong className="tile-value" key={currency}>
                    {formatMinorUnits(minor)} {currency}
                  </strong>
                ))
              )}
            </div>

            <div className="tile">
              <span className="tile-label">By status</span>
              <div className="status-breakdown">
                {STATUSES.map((status) => (
                  <span key={status}>
                    <em className={`pill pill-${status}`}>{status}</em> {statusCounts[status]}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section>
          <div className="section-head">
            <h2>All Accounts</h2>
            <button type="button" className="ghost" onClick={load} disabled={loading}>
              {loading ? 'Loading…' : 'Refresh'}
            </button>
          </div>

          <div className="controls">
            <input
              type="search"
              placeholder="Search number, holder or owner"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Search accounts"
            />

            <label>
              Status
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
              >
                <option value="all">All</option>
                {STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Sort by
              <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
                <option value="account_number">Account number</option>
                <option value="account_holder_name">Holder</option>
                <option value="balance">Balance (high to low)</option>
                <option value="date_opened">Date opened</option>
              </select>
            </label>
          </div>

          <div className="account-table">
            <div className="account-row account-header">
              <span>Account</span>
              <span>Holder</span>
              <span>Type</span>
              <span>Opened</span>
              <span>Balance</span>
              <span>Status</span>
              <span />
            </div>

            {loading && accounts.length === 0 && (
              <p className="empty">Loading accounts…</p>
            )}

            {!loading && visibleAccounts.length === 0 && (
              <p className="empty">
                {accounts.length === 0
                  ? 'No accounts yet.'
                  : 'No accounts match this filter.'}
              </p>
            )}

            {visibleAccounts.map((account) => (
              <div className="account-row" key={account.account_number}>
                <span>#{account.account_number}</span>
                <span>
                  {account.account_holder_name}
                  <small>{account.owner_id}</small>
                </span>
                <span>{account.account_type.replace('_', ' ')}</span>
                <span>{account.date_opened}</span>
                <strong>
                  {formatMoney(account.balance)} {account.currency}
                </strong>

                <span>
                  <select
                    value={account.status}
                    disabled={busyAccount === account.account_number}
                    onChange={(event) => changeStatus(account, event.target.value)}
                    aria-label={`Status for account ${account.account_number}`}
                  >
                    {STATUSES.map((status) => (
                      <option key={status} value={status}>
                        {status}
                      </option>
                    ))}
                  </select>
                </span>

                <span>
                  <button
                    type="button"
                    className="danger"
                    disabled={busyAccount === account.account_number}
                    onClick={() => remove(account)}
                  >
                    Delete
                  </button>
                </span>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2>Recent Transfers</h2>

          <div className="transfer-table">
            <div className="transfer-row transfer-header">
              <span>When</span>
              <span>From</span>
              <span>To</span>
              <span>Description</span>
              <span>Amount</span>
            </div>

            {transfers.length === 0 && <p className="empty">No transfers yet.</p>}

            {transfers.map((transfer) => (
              <div className="transfer-row" key={transfer.id}>
                <span>{String(transfer.timestamp).slice(0, 10)}</span>
                <span>#{transfer.from_account_number}</span>
                <span>#{transfer.to_account_number}</span>
                <span>{transfer.description || '—'}</span>
                <strong>
                  {formatMoney(transfer.amount)} {transfer.currency}
                </strong>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2>Registered Customers</h2>

          <div className="user-table">
            <div className="user-row user-header">
              <span>Name</span>
              <span>Email</span>
              <span>Registered</span>
            </div>

            {users.length === 0 && <p className="empty">No customers yet.</p>}

            {users.map((user) => (
              <div className="user-row" key={user.id}>
                <span>{user.full_name}</span>
                <span>{user.email}</span>
                <span>{String(user.created_at).slice(0, 10)}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  )
}

export default AdminHome
