import { Input } from "./ui/input";
import "./theme.css";

export default function StyleSelector() {
  // TODO: Initially set the color based on the document style
  return (
    <div className="style-selector">
      <Input type="color" onChange={(e) => {document.documentElement.style.setProperty('--base-color', e.target.value);}}/>
    </div>
  );
}
