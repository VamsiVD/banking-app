import { useCallback, useEffect, useState } from 'react'
import './UserHome.css'
import { api } from './api/client.js'

/**
 * Money crosses the wire as a JSON *string* (see AdminHome.jsx), because the
 * API models it as a Decimal and a float cannot hold 0.10 exactly. Keep it a
 * string all the way to the screen — `.toFixed()` on a string throws.
 */
function formatMoney(amount) {
    const [whole, fraction = ''] = String(amount).split('.')
    const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
    return `${grouped}.${fraction.padEnd(2, '0').slice(0, 2)}`
}

function UserHome({ user, onBack }) {
    const [fullName, setFullName] = useState(user.email)
    const [accounts, setAccounts] = useState([])
    const [transfers, setTransfers] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    const [showNewAccountForm, setShowNewAccountForm] = useState(false)
    const [newAccountType, setNewAccountType] = useState('checking')
    const [creatingAccount, setCreatingAccount] = useState(false)
    const [createError, setCreateError] = useState(null)

    const load = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            // No "my accounts" endpoint exists yet, so filter the full list down
            // to this customer's own — same trade-off AdminHome's search makes,
            // just narrowed to one owner instead of left open.
            const allAccounts = await api.get('/accounts/')
            const ownAccounts = allAccounts.filter(
                (account) => account.owner_id.toLowerCase() === user.email.toLowerCase(),
            )
            setAccounts(ownAccounts)

            // A decorative lookup only — the page still works without a name.
            api
                .get(`/auth/users/${encodeURIComponent(user.email)}`)
                .then((profile) => setFullName(profile.full_name))
                .catch(() => {})

            // Transfers are scoped per account_number, so one call per account
            // the customer actually owns, merged and deduplicated (a transfer
            // between two of their own accounts would otherwise show up twice).
            const pages = await Promise.all(
                ownAccounts.map((account) =>
                    api.get(`/transfers?account_number=${encodeURIComponent(account.account_number)}&limit=10`),
                ),
            )
            const byId = new Map()
            for (const page of pages) {
                for (const transfer of page.items) byId.set(transfer.id, transfer)
            }
            const merged = [...byId.values()].sort(
                (a, b) => new Date(b.timestamp) - new Date(a.timestamp),
            )
            setTransfers(merged.slice(0, 10))
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }, [user.email])

    useEffect(() => {
        load()
    }, [load])

    async function handleCreateAccount(event) {
        event.preventDefault()
        setCreatingAccount(true)
        setCreateError(null)
        try {
            const created = await api.post('/accounts/', {
                account_holder_name: fullName,
                account_type: newAccountType,
                status: 'active',
                currency: 'USD',
                owner_id: user.email,
            })
            setAccounts((current) => [...current, created])
            setShowNewAccountForm(false)
        } catch (err) {
            setCreateError(err.message)
        } finally {
            setCreatingAccount(false)
        }
    }

    return (
        <main className="user-home">
            <header className="top-bar">
                <div>
                    <h1>Banks-<span style={{ display: 'inline-block', transform: 'scaleX(-1)' }}>R</span>-Us</h1>
                </div>

                <button type="button" onClick={onBack}>
                    Sign Out
                </button>
            </header>

            <div className="page-content">
                {error && (
                    <p className="banner banner-error" role="alert">
                        {error}
                    </p>
                )}

                <section className="summary">
                    <h1>Account Overview</h1>
                    <h2 className="user-greeting">
                        Welcome, {fullName}
                    </h2>
                    <p>{user.email}</p>
                </section>

                <section>
                    <div className="section-head">
                        <h2>Your Accounts</h2>
                        <button
                            type="button"
                            className="ghost"
                            onClick={() => {
                                setShowNewAccountForm((current) => !current)
                                setCreateError(null)
                            }}
                        >
                            {showNewAccountForm ? 'Cancel' : 'New Account'}
                        </button>
                    </div>

                    {showNewAccountForm && (
                        <form className="new-account-form" onSubmit={handleCreateAccount}>
                            <label htmlFor="new-account-type">
                                Account type
                                <select
                                    id="new-account-type"
                                    value={newAccountType}
                                    onChange={(event) => setNewAccountType(event.target.value)}
                                >
                                    <option value="checking">Checking</option>
                                    <option value="savings">Savings</option>
                                    <option value="business">Business</option>
                                    <option value="fixed_deposit">Fixed deposit</option>
                                </select>
                            </label>

                            {createError && (
                                <p className="banner banner-error" role="alert">
                                    {createError}
                                </p>
                            )}

                            <button type="submit" disabled={creatingAccount}>
                                {creatingAccount ? 'Opening…' : 'Open Account'}
                            </button>
                        </form>
                    )}

                    <div className="account-table">
                        <div className="account-row account-header">
                            <span>Account</span>
                            <span>Type</span>
                            <span>Status</span>
                            <span>Opened</span>
                            <span>Balance</span>
                        </div>

                        {loading && accounts.length === 0 && (
                            <p className="empty">Loading accounts…</p>
                        )}

                        {!loading && accounts.length === 0 && (
                            <p className="empty">No accounts yet.</p>
                        )}

                        {accounts.map((account) => (
                            <div className="account-row" key={account.account_number}>
                                <span>#{account.account_number}</span>
                                <span>{account.account_type.replace('_', ' ')}</span>
                                <span>{account.status}</span>
                                <span>{account.date_opened}</span>
                                <strong>
                                    {formatMoney(account.balance)} {account.currency}
                                </strong>
                            </div>
                        ))}
                    </div>
                </section>

                <section>
                    <h2>Quick Actions</h2>

                    <div className="action-row">
                        <button type="button">Transfer</button>
                        <button type="button">Deposit</button>
                        <button type="button">Withdraw</button>
                        <button type="button">Statement</button>
                    </div>
                </section>

                <section>
                    <h2>Recent Transfers</h2>

                    <div className="transaction-table">
                        <div className="transaction-row transaction-header">
                            <span>Date</span>
                            <span>From</span>
                            <span>To</span>
                            <span>Description</span>
                            <span>Amount</span>
                        </div>

                        {!loading && transfers.length === 0 && (
                            <p className="empty">No transfers yet.</p>
                        )}

                        {transfers.map((transfer) => (
                            <div className="transaction-row" key={transfer.id}>
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
            </div>
        </main>
    )
}

export default UserHome
