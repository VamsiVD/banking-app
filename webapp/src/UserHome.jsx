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

const ACTION_LABELS = {
    transfer: { title: 'Transfer between accounts', submit: 'Send Transfer' },
    deposit: { title: 'Deposit funds', submit: 'Deposit' },
    withdraw: { title: 'Withdraw funds', submit: 'Withdraw' },
    statement: { title: 'Account statement', submit: 'Get Statement' },
}

const MS_PER_DAY = 24 * 60 * 60 * 1000

function capitalize(word) {
    return word.charAt(0).toUpperCase() + word.slice(1)
}

// Money is a Decimal server-side, so `amount` arrives as a string (see
// formatMoney's comment above) — Number() here is only for arithmetic on the
// summary totals, never for display.
function monthlyEquivalent(subscription) {
    const amount = Number(subscription.amount)
    return subscription.billing_cycle === 'yearly' ? amount / 12 : amount
}

function daysUntil(dateString) {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const target = new Date(dateString)
    return Math.round((target - today) / MS_PER_DAY)
}

const ACTION_ICONS = {
    transfer: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M4 8h13M13 4l4 4-4 4M20 16H7m4 4-4-4 4-4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    ),
    deposit: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M12 4v11m0 0 4-4m-4 4-4-4M5 19h14" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    ),
    withdraw: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M12 20V9m0 0 4 4m-4-4-4 4M5 5h14" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    ),
    statement: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M7 3h8l4 4v14H7z" strokeLinejoin="round" />
            <path d="M9 12h6M9 16h6M9 8h2" strokeLinecap="round" />
        </svg>
    ),
}

function AccountIcon() {
    return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="3" y="7" width="18" height="12" rx="1.5" />
            <path d="M3 10h18M7 15h4" strokeLinecap="round" />
        </svg>
    )
}

function UserHome({ user, onBack }) {
    const [fullName, setFullName] = useState(user.email)
    const [accounts, setAccounts] = useState([])
    const [transfers, setTransfers] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [notice, setNotice] = useState(null)

    const [showNewAccountForm, setShowNewAccountForm] = useState(false)
    const [newAccountType, setNewAccountType] = useState('checking')
    const [creatingAccount, setCreatingAccount] = useState(false)
    const [createError, setCreateError] = useState(null)

    const [subscriptions, setSubscriptions] = useState([])
    const [showAddSubscription, setShowAddSubscription] = useState(false)
    const [subName, setSubName] = useState('')
    const [subAmount, setSubAmount] = useState('')
    const [subCurrency, setSubCurrency] = useState('USD')
    const [subBillingCycle, setSubBillingCycle] = useState('monthly')
    const [subNextBillingDate, setSubNextBillingDate] = useState('')
    const [creatingSubscription, setCreatingSubscription] = useState(false)
    const [subscriptionError, setSubscriptionError] = useState(null)
    const [deletingSubscriptionId, setDeletingSubscriptionId] = useState(null)

    // Which Quick Action form is open — 'transfer' | 'deposit' | 'withdraw' | 'statement' | null.
    const [activeAction, setActiveAction] = useState(null)
    const [actionAccount, setActionAccount] = useState('')
    const [toAccount, setToAccount] = useState('')
    const [amount, setAmount] = useState('')
    const [description, setDescription] = useState('')
    const [submittingAction, setSubmittingAction] = useState(false)
    const [actionError, setActionError] = useState(null)
    const [statementResult, setStatementResult] = useState(null)

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
                .catch(() => { })

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

            // Scoped to the caller by owner_id server-side already — no
            // client-side filtering needed, unlike the accounts list above.
            const ownSubscriptions = await api.get('/subscriptions/')
            setSubscriptions(ownSubscriptions)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }, [user.email])

    useEffect(() => {
        load()
    }, [load])

    function openAction(action) {
        setActiveAction(action)
        setActionAccount(accounts[0]?.account_number ?? '')
        setToAccount('')
        setAmount('')
        setDescription('')
        setActionError(null)
        setStatementResult(null)
    }

    async function handleActionSubmit(event) {
        event.preventDefault()
        setSubmittingAction(true)
        setActionError(null)
        setNotice(null)
        setStatementResult(null)
        try {
            if (activeAction === 'deposit') {
                const txn = await api.post(`/accounts/${actionAccount}/deposit`, {
                    amount,
                    description: description || undefined,
                })
                setNotice(
                    `Deposited ${formatMoney(txn.amount)} ${txn.currency} into #${txn.account_number}. New balance: ${formatMoney(txn.balance_after)} ${txn.currency}.`,
                )
            } else if (activeAction === 'withdraw') {
                const txn = await api.post(`/accounts/${actionAccount}/withdraw`, {
                    amount,
                    description: description || undefined,
                })
                setNotice(
                    `Withdrew ${formatMoney(txn.amount)} ${txn.currency} from #${txn.account_number}. New balance: ${formatMoney(txn.balance_after)} ${txn.currency}.`,
                )
            } else if (activeAction === 'transfer') {
                const result = await api.post('/transfers', {
                    from_account_number: actionAccount,
                    to_account_number: toAccount,
                    amount,
                    description: description || undefined,
                })
                setNotice(
                    `Transferred ${formatMoney(result.debit.amount)} ${result.debit.currency} from #${actionAccount} to #${toAccount}.`,
                )
            } else if (activeAction === 'statement') {
                // Read-only: leave the panel open so the figures stay visible,
                // and skip `load()` — nothing about the account data changed.
                setStatementResult(await api.get(`/accounts/${actionAccount}/statement`))
            }

            if (activeAction !== 'statement') {
                setActiveAction(null)
                await load()
            }
        } catch (err) {
            setActionError(err.message)
        } finally {
            setSubmittingAction(false)
        }
    }

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

    async function handleCreateSubscription(event) {
        event.preventDefault()
        setCreatingSubscription(true)
        setSubscriptionError(null)
        try {
            const created = await api.post('/subscriptions/', {
                name: subName,
                amount: subAmount,
                currency: subCurrency,
                billing_cycle: subBillingCycle,
                next_billing_date: subNextBillingDate,
            })
            setSubscriptions((current) => [...current, created])
            setShowAddSubscription(false)
            setSubName('')
            setSubAmount('')
            setSubCurrency('USD')
            setSubBillingCycle('monthly')
            setSubNextBillingDate('')
        } catch (err) {
            setSubscriptionError(err.message)
        } finally {
            setCreatingSubscription(false)
        }
    }

    async function handleDeleteSubscription(id) {
        setDeletingSubscriptionId(id)
        setSubscriptionError(null)
        try {
            await api.delete(`/subscriptions/${id}`)
            setSubscriptions((current) => current.filter((sub) => sub.id !== id))
        } catch (err) {
            setSubscriptionError(err.message)
        } finally {
            setDeletingSubscriptionId(null)
        }
    }

    const monthlySpend = subscriptions.reduce((sum, sub) => sum + monthlyEquivalent(sub), 0)
    const annualSpend = monthlySpend * 12
    const upcomingRenewals = subscriptions.filter((sub) => {
        const days = daysUntil(sub.next_billing_date)
        return days >= 0 && days <= 7
    })

    // Grouped by currency rather than summed blindly across all of them — an
    // account balance in USD and one in EUR are not the same number.
    const balanceByCurrency = accounts.reduce((totals, account) => {
        totals[account.currency] = (totals[account.currency] ?? 0) + Number(account.balance)
        return totals
    }, {})

    return (
        <main className="user-home">
            <header className="top-bar">
                <div className="brand">
                    Banks-<span style={{ display: 'inline-block', transform: 'scaleX(-1)' }}>R</span>-Us
                </div>

                <button type="button" className="sign-out-btn" onClick={onBack}>
                    Sign Out
                </button>
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

                <section className="hero">
                    <h1 className="hero-greeting">Welcome back, {fullName}.</h1>

                    <div className="balance-card">
                        <span className="balance-label">Total Balance</span>

                        {Object.keys(balanceByCurrency).length === 0 ? (
                            <div className="balance-amount">—</div>
                        ) : (
                            Object.entries(balanceByCurrency).map(([currency, total]) => (
                                <div className="balance-amount" key={currency}>
                                    {formatMoney(total.toFixed(2))} {currency}
                                </div>
                            ))
                        )}

                        <span className="balance-sub">
                            {accounts.length} account{accounts.length === 1 ? '' : 's'}
                        </span>
                    </div>
                </section>

                <section className="section-accounts">
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

                    <div className="account-grid">
                        {loading && accounts.length === 0 && (
                            <p className="empty">Loading accounts…</p>
                        )}

                        {!loading && accounts.length === 0 && (
                            <p className="empty">No accounts yet.</p>
                        )}

                        {accounts.map((account) => (
                            <div className="account-card" key={account.account_number}>
                                <div className="account-card-head">
                                    <span className="account-icon">
                                        <AccountIcon />
                                    </span>
                                    <span className={`status-pill status-${account.status}`}>
                                        {account.status}
                                    </span>
                                </div>
                                <div className="account-type">{account.account_type.replace('_', ' ')}</div>
                                <div className="account-balance">
                                    {formatMoney(account.balance)} {account.currency}
                                </div>
                                <div className="account-meta">
                                    #{account.account_number} · opened {account.date_opened}
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                <section className="section-quick-actions">
                    <h2>Quick Actions</h2>

                    <div className="action-row">
                        <button
                            type="button"
                            className="qa-btn qa-btn-primary"
                            disabled={accounts.length === 0}
                            onClick={() => openAction('transfer')}
                        >
                            <span className="qa-icon">{ACTION_ICONS.transfer}</span>
                            Transfer
                        </button>
                        <button
                            type="button"
                            className="qa-btn qa-btn-primary"
                            disabled={accounts.length === 0}
                            onClick={() => openAction('deposit')}
                        >
                            <span className="qa-icon">{ACTION_ICONS.deposit}</span>
                            Deposit
                        </button>
                        <button
                            type="button"
                            className="qa-btn qa-btn-primary"
                            disabled={accounts.length === 0}
                            onClick={() => openAction('withdraw')}
                        >
                            <span className="qa-icon">{ACTION_ICONS.withdraw}</span>
                            Withdraw
                        </button>
                        <button
                            type="button"
                            className="qa-btn qa-btn-primary"
                            disabled={accounts.length === 0}
                            onClick={() => openAction('statement')}
                        >
                            <span className="qa-icon">{ACTION_ICONS.statement}</span>
                            Statement
                        </button>
                    </div>

                    {activeAction && (
                        <form className="quick-action-form" onSubmit={handleActionSubmit}>
                            <h3>{ACTION_LABELS[activeAction].title}</h3>

                            <div className="quick-action-fields">
                                <label>
                                    {activeAction === 'transfer' ? 'From account' : 'Account'}
                                    <select
                                        value={actionAccount}
                                        onChange={(event) => setActionAccount(event.target.value)}
                                        required
                                    >
                                        {accounts.map((account) => (
                                            <option key={account.account_number} value={account.account_number}>
                                                #{account.account_number} — {account.account_type.replace('_', ' ')} ({formatMoney(account.balance)} {account.currency})
                                            </option>
                                        ))}
                                    </select>
                                </label>

                                {activeAction === 'transfer' && (
                                    <label>
                                        To account
                                        <input
                                            type="text"
                                            value={toAccount}
                                            onChange={(event) => setToAccount(event.target.value)}
                                            placeholder="Account number"
                                            required
                                        />
                                    </label>
                                )}

                                {activeAction !== 'statement' && (
                                    <label>
                                        Amount
                                        <input
                                            type="number"
                                            min="0.01"
                                            step="0.01"
                                            value={amount}
                                            onChange={(event) => setAmount(event.target.value)}
                                            required
                                        />
                                    </label>
                                )}

                            </div>

                            {actionError && (
                                <p className="banner banner-error" role="alert">
                                    {actionError}
                                </p>
                            )}

                            <div className="quick-action-buttons">
                                <button type="submit" disabled={submittingAction}>
                                    {submittingAction ? 'Submitting…' : ACTION_LABELS[activeAction].submit}
                                </button>
                                <button type="button" className="ghost" onClick={() => setActiveAction(null)}>
                                    Cancel
                                </button>
                            </div>

                            {activeAction === 'statement' && statementResult && (
                                <div className="statement-result">
                                    <div className="statement-result-row">
                                        <span>Opening balance</span>
                                        <strong>
                                            {formatMoney(statementResult.opening_balance)} {statementResult.currency}
                                        </strong>
                                    </div>
                                    <div className="statement-result-row">
                                        <span>Closing balance</span>
                                        <strong>
                                            {formatMoney(statementResult.closing_balance)} {statementResult.currency}
                                        </strong>
                                    </div>
                                    <div className="statement-result-row">
                                        <span>Total in</span>
                                        <strong>
                                            {formatMoney(statementResult.total_in)} {statementResult.currency}
                                        </strong>
                                    </div>
                                    <div className="statement-result-row">
                                        <span>Total out</span>
                                        <strong>
                                            {formatMoney(statementResult.total_out)} {statementResult.currency}
                                        </strong>
                                    </div>
                                    <div className="statement-result-row">
                                        <span>Entries</span>
                                        <strong>{statementResult.entry_count}</strong>
                                    </div>
                                </div>
                            )}
                        </form>
                    )}
                </section>

                <section className="section-transfers">
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

                <section className="section-subscriptions">
                    <div className="section-head">
                        <h2>Subscriptions</h2>
                        <button
                            type="button"
                            className="ghost"
                            onClick={() => {
                                setShowAddSubscription((current) => !current)
                                setSubscriptionError(null)
                            }}
                        >
                            {showAddSubscription ? 'Cancel' : 'Add Subscription'}
                        </button>
                    </div>

                    <div className="subscription-summary">
                        <div className="subscription-summary-card">
                            <span className="subscription-summary-label">Monthly Spend</span>
                            <strong>{formatMoney(monthlySpend)} USD</strong>
                        </div>
                        <div className="subscription-summary-card">
                            <span className="subscription-summary-label">Annual Spend</span>
                            <strong>{formatMoney(annualSpend)} USD</strong>
                        </div>
                        <div className="subscription-summary-card subscription-summary-highlight">
                            <span className="subscription-summary-label">Renewing in 7 Days</span>
                            <strong>{upcomingRenewals.length}</strong>
                        </div>
                    </div>

                    {showAddSubscription && (
                        <form className="new-account-form" onSubmit={handleCreateSubscription}>
                            <label htmlFor="sub-name">
                                Service name
                                <input
                                    id="sub-name"
                                    type="text"
                                    value={subName}
                                    onChange={(event) => setSubName(event.target.value)}
                                    required
                                />
                            </label>

                            <label htmlFor="sub-amount">
                                Amount
                                <input
                                    id="sub-amount"
                                    type="number"
                                    min="0.01"
                                    step="0.01"
                                    value={subAmount}
                                    onChange={(event) => setSubAmount(event.target.value)}
                                    required
                                />
                            </label>

                            <label htmlFor="sub-currency">
                                Currency
                                <input
                                    id="sub-currency"
                                    type="text"
                                    value={subCurrency}
                                    onChange={(event) => setSubCurrency(event.target.value.toUpperCase())}
                                    maxLength={3}
                                    pattern="[A-Z]{3}"
                                    title="Three-letter currency code, e.g. USD"
                                    required
                                />
                            </label>

                            <label htmlFor="sub-billing-cycle">
                                Billing cycle
                                <select
                                    id="sub-billing-cycle"
                                    value={subBillingCycle}
                                    onChange={(event) => setSubBillingCycle(event.target.value)}
                                >
                                    <option value="monthly">Monthly</option>
                                    <option value="yearly">Yearly</option>
                                </select>
                            </label>

                            <label htmlFor="sub-next-billing-date">
                                Next billing date
                                <input
                                    id="sub-next-billing-date"
                                    type="date"
                                    value={subNextBillingDate}
                                    onChange={(event) => setSubNextBillingDate(event.target.value)}
                                    required
                                />
                            </label>

                            {subscriptionError && (
                                <p className="banner banner-error" role="alert">
                                    {subscriptionError}
                                </p>
                            )}

                            <button type="submit" disabled={creatingSubscription}>
                                {creatingSubscription ? 'Adding…' : 'Add Subscription'}
                            </button>
                        </form>
                    )}

                    {!showAddSubscription && subscriptionError && (
                        <p className="banner banner-error" role="alert">
                            {subscriptionError}
                        </p>
                    )}

                    <div className="account-table">
                        <div className="account-row subscription-row account-header">
                            <span>Service</span>
                            <span>Cycle</span>
                            <span>Amount</span>
                            <span>Next Billing</span>
                            <span>Actions</span>
                        </div>

                        {loading && subscriptions.length === 0 && (
                            <p className="empty">Loading subscriptions…</p>
                        )}

                        {!loading && subscriptions.length === 0 && (
                            <p className="empty">No subscriptions yet.</p>
                        )}

                        {subscriptions.map((subscription) => (
                            <div className="account-row subscription-row" key={subscription.id}>
                                <span>{subscription.name}</span>
                                <span>{capitalize(subscription.billing_cycle)}</span>
                                <strong>
                                    {formatMoney(subscription.amount)} {subscription.currency}
                                </strong>
                                <span>{subscription.next_billing_date}</span>
                                <button
                                    type="button"
                                    className="ghost"
                                    disabled={deletingSubscriptionId === subscription.id}
                                    onClick={() => handleDeleteSubscription(subscription.id)}
                                >
                                    {deletingSubscriptionId === subscription.id ? 'Removing…' : 'Cancel'}
                                </button>
                            </div>
                        ))}
                    </div>
                </section>
            </div>
        </main>
    )
}

export default UserHome
