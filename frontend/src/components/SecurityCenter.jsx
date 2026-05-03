export default function SecurityCenter({
  user,
  stats,
  securityOverview,
  resetForm,
  setResetForm,
  onPasswordReset,
  onRevokeSessions,
  working,
  message,
  error,
}) {
  const recentAlerts = securityOverview?.recent_security_alerts || [];
  const recentLogs = securityOverview?.recent_audit_logs || [];
  const canSeeDashboard = user?.is_admin || user?.role === "security_analyst";

  return (
    <section className="security-center-page">
      <div className="security-hero">
        <div>
          <p className="eyebrow">Security center</p>
          <h1>Protect accounts, review alerts, and manage active access.</h1>
          <p className="security-hero-copy">
            This workspace now includes password reset, session revocation, failed-login protection, audit logging, and a security dashboard for monitoring suspicious activity.
          </p>
        </div>
        <div className="security-hero-badges">
          <span>RBAC</span>
          <span>Audit logs</span>
          <span>Security alerts</span>
          <span>Session control</span>
        </div>
      </div>

      <div className="security-center-grid">
        <section className="security-card">
          <div className="security-card-head">
            <div>
              <p className="eyebrow">Account security</p>
              <h3>Password reset</h3>
            </div>
          </div>
          <p className="security-card-copy">
            Reset your password using your registered email and phone number. This will rotate your session token and keep this session active with a fresh token.
          </p>
          <form className="security-form" onSubmit={onPasswordReset}>
            <label>
              Email
              <input
                type="email"
                value={resetForm.email}
                onChange={(event) => setResetForm((current) => ({ ...current, email: event.target.value }))}
                placeholder="you@example.com"
              />
            </label>
            <label>
              Phone number
              <input
                type="tel"
                value={resetForm.phone}
                onChange={(event) => setResetForm((current) => ({ ...current, phone: event.target.value }))}
                placeholder="Registered phone number"
              />
            </label>
            <label>
              New password
              <input
                type="password"
                value={resetForm.new_password}
                onChange={(event) => setResetForm((current) => ({ ...current, new_password: event.target.value }))}
                placeholder="New password"
              />
            </label>
            <button type="submit" className="security-primary-button" disabled={working}>
              Reset password
            </button>
          </form>
        </section>

        <section className="security-card">
          <div className="security-card-head">
            <div>
              <p className="eyebrow">Session control</p>
              <h3>Revoke other sessions</h3>
            </div>
          </div>
          <p className="security-card-copy">
            Force sign-out on other devices while keeping this one active. Useful if you shared a token, used a public machine, or suspect account misuse.
          </p>
          <div className="security-user-summary">
            <strong>{user?.name}</strong>
            <span>{user?.email}</span>
            <span className="security-role-chip">{user?.role || "user"}</span>
          </div>
          <button type="button" className="security-secondary-button" onClick={onRevokeSessions} disabled={working}>
            Revoke all other sessions
          </button>
          {message ? <p className="security-success">{message}</p> : null}
          {error ? <p className="security-error">{error}</p> : null}
        </section>
      </div>

      {canSeeDashboard ? (
        <>
          {stats ? (
            <div className="security-stats-grid">
              <article className="security-stat-card"><strong>{stats.audit_log_count}</strong><span>Audit logs</span></article>
              <article className="security-stat-card"><strong>{stats.open_security_alert_count}</strong><span>Open alerts</span></article>
              <article className="security-stat-card"><strong>{stats.failed_login_count}</strong><span>Login risk records</span></article>
              <article className="security-stat-card"><strong>{stats.user_count}</strong><span>Total users</span></article>
            </div>
          ) : null}

          <div className="security-center-grid security-dashboard-grid">
            <section className="security-card">
              <div className="security-card-head">
                <div>
                  <p className="eyebrow">Alert stream</p>
                  <h3>Recent security alerts</h3>
                </div>
              </div>
              <div className="security-feed">
                {recentAlerts.length ? recentAlerts.slice(0, 8).map((alert) => (
                  <article key={alert.id} className="security-feed-card">
                    <div className="security-feed-top">
                      <strong>{alert.alert_type}</strong>
                      <span className={`security-severity-chip ${alert.severity}`}>{alert.severity}</span>
                    </div>
                    <p>{alert.message}</p>
                    <span>{alert.user_email || alert.ip_address || "System"}</span>
                  </article>
                )) : <p className="empty-mini">No alerts right now.</p>}
              </div>
            </section>

            <section className="security-card">
              <div className="security-card-head">
                <div>
                  <p className="eyebrow">Audit trail</p>
                  <h3>Recent audit events</h3>
                </div>
              </div>
              <div className="security-feed">
                {recentLogs.length ? recentLogs.slice(0, 10).map((log) => (
                  <article key={log.id} className="security-feed-card">
                    <div className="security-feed-top">
                      <strong>{log.event_type}</strong>
                      <span className={`security-severity-chip ${log.severity}`}>{log.severity}</span>
                    </div>
                    <p>{log.description}</p>
                    <span>{log.actor_email || log.ip_address || "System"}</span>
                  </article>
                )) : <p className="empty-mini">No audit events yet.</p>}
              </div>
            </section>
          </div>
        </>
      ) : null}
    </section>
  );
}
