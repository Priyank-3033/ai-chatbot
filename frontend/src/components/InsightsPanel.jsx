export default function InsightsPanel({ contact, knowledgeCards, lastSources }) {
  return (
    <aside className="insights-card">
      <section className="profile-panel">
        <p className="section-kicker">Customer</p>
        <div className="profile-row">
          <div className="avatar-orb">{contact.initials}</div>
          <div>
            <h3>{contact.name}</h3>
            <p>{contact.plan}</p>
          </div>
        </div>
        <div className="profile-grid">
          <div>
            <span>Health</span>
            <strong>{contact.health}</strong>
          </div>
          <div>
            <span>MRR</span>
            <strong>{contact.mrr}</strong>
          </div>
          <div>
            <span>Region</span>
            <strong>{contact.region}</strong>
          </div>
          <div>
            <span>Owner</span>
            <strong>{contact.owner}</strong>
          </div>
        </div>
      </section>

      <section className="helper-panel">
        <p className="section-kicker">Suggested Reply Focus</p>
        <ul className="detail-list">
          <li>Lead with the current policy in one sentence.</li>
          <li>Offer a next action instead of ending at "not possible".</li>
          <li>Escalate if there is any ownership or security conflict.</li>
        </ul>
      </section>

      <section className="helper-panel">
        <p className="section-kicker">Recent Sources</p>
        <div className="tag-list">
          {lastSources.map((source) => (
            <span key={source} className="source-tag">
              {source}
            </span>
          ))}
        </div>
      </section>

      <section className="helper-panel">
        <p className="section-kicker">Knowledge Base</p>
        <div className="knowledge-list">
          {knowledgeCards.map((card) => (
            <article key={card.title} className="knowledge-card">
              <h4>{card.title}</h4>
              <p>{card.detail}</p>
            </article>
          ))}
        </div>
      </section>
    </aside>
  );
}
