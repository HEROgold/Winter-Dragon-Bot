import "./index.css";
import { Routes } from "./routes";
import { AuthProvider } from "./contexts/AuthContext";

export function App() {
  return (
    <AuthProvider>
      <Routes />
    </AuthProvider>
  );
}

export default App;
