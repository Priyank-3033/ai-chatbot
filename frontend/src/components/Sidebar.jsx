export default function Sidebar({ items, activeId, onSelect }) {
  return (
    <aside className="sidebar-card">
      <div className="brand-block">
        <div className="brand-mark">S</div>
        <div>
          <p className="section-kicker">Support Pilot</p>
          <h1>Inbox</h1>
        </div>
      </div>

      <div className="metric-strip">
        <div>
          <span>24</span>
          <p>Open Tickets</p>
        </div>
        <div>
          <span>4m</span>
          <p>Avg First Reply</p>
        </div>
      </div>

      <div className="conversation-list">
        {items.map((item) => (
          <button
            key={item.id}
            className={`conversation-card ${activeId === item.id ? "active" : ""}`}
            onClick={() => onSelect(item.id)}
          >
            <div className="conversation-topline">
              <strong>{item.customer}</strong>
              <span>{item.waitTime}</span>
            </div>
            <div className="conversation-meta">
              <span>{item.channel}</span>
              <span className={`priority-chip ${item.priority.toLowerCase()}`}>
                {item.priority}
              </span>
            </div>
            <p>{item.preview}</p>
          </button>
        ))}
      </div>
    </aside>
  );
}
