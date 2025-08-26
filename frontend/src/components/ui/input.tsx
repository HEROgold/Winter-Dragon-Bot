import "./input.css"

export function Input(properties: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className="input" {...properties} />;
}
