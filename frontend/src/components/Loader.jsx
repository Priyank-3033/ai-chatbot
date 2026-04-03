export default function Loader({ label = "AI is typing..." }) {
  return (
    <div className="typing-indicator" aria-label={label}>
      <span />
      <span />
      <span />
    </div>
  );
}
