import './UserHome.css'

function UserHome({ onBack }) {
    const user = {
        full_name: 'Lars Dill',
        email: 'lars7@gmail.com',
    }
    const accounts = [
        {
            account_number: '790',
            account_holder_name: 'Lars Dill',
            account_type: 'checking',
            status: 'active',
            balance: 2450.75,
            currency: 'USD',
            date_opened: '2026-08-01',
            owner_id: 'lars7@gmail.com',
        },
        {
            account_number: '791',
            account_holder_name: 'Lars Dill',
            account_type: 'savings',
            status: 'active',
            balance: 6200.0,
            currency: 'USD',
            date_opened: '2026-08-10',
            owner_id: 'lars7@gmail.com',
        },
    ]
    const transactions = [
        {
            id: 'txn-001',
            account_number: '790',
            type: 'deposit',
            amount: 500.0,
            currency: 'USD',
            balance_after: 2450.75,
            counterparty: null,
            description: 'Paycheck deposit',
            created_at: '2026-08-26',
        },
        {
            id: 'txn-002',
            account_number: '790',
            type: 'withdrawal',
            amount: 50.0,
            currency: 'USD',
            balance_after: 1950.75,
            counterparty: null,
            description: 'ATM withdrawal',
            created_at: '2026-08-25',
        },
        {
            id: 'txn-003',
            account_number: '790',
            type: 'transfer_out',
            amount: 120.0,
            currency: 'USD',
            balance_after: 1830.75,
            counterparty: '791',
            description: 'Transfer to Savings',
            created_at: '2026-08-24',
        },
        {
            id: 'txn-004',
            account_number: '791',
            type: 'transfer_in',
            amount: 120.0,
            currency: 'USD',
            balance_after: 6200.0,
            counterparty: '790',
            description: 'Transfer from Checking',
            created_at: '2026-08-24',
        },
    ]
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
                <section className="summary">
                    <h1>Account Overview</h1>
                    <h2 className="user-greeting">
                        Welcome, {user.full_name}
                    </h2>
                    <p>{user.email}</p>
                </section>

                <section>
                    <h2>Your Accounts</h2>

                    <div className="account-table">
                        <div className="account-row account-header">
                            <span>Account</span>
                            <span>Type</span>
                            <span>Status</span>
                            <span>Opened</span>
                            <span>Balance</span>
                        </div>

                        {accounts.map((account) => (
                            <div className="account-row" key={account.account_number}>
                                <span>#{account.account_number}</span>
                                <span>{account.account_type}</span>
                                <span>{account.status}</span>
                                <span>{account.date_opened}</span>
                                <strong>
                                    ${account.balance.toFixed(2)} {account.currency}
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
                    <h2>Recent Transactions</h2>

                    <div className="transaction-table">
                        <div className="transaction-row transaction-header">
                            <span>Date</span>
                            <span>Type</span>
                            <span>Account</span>
                            <span>Description</span>
                            <span>Amount</span>
                        </div>

                        {transactions.map((transaction) => (
                            <div className="transaction-row" key={transaction.id}>
                                <span>{transaction.created_at}</span>
                                <span>{transaction.type.replace('_', ' ')}</span>
                                <span>#{transaction.account_number}</span>
                                <span>{transaction.description}</span>
                                <strong>
                                    ${transaction.amount.toFixed(2)}
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