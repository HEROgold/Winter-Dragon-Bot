
// Todo, add inline styling using new css `if` syntax etc.
import "./button.css"

export default function Button(properties: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button className="btn" {...properties}>
        {properties.children}
    </button>
  );
}
