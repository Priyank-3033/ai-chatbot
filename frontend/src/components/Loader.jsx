export default function Loader({ label = "Typing..." }) {
  return (
    <div className="typing-indicator" aria-label={label}>
      <span />
      <span />
      <span />
    </div>
  );
}
