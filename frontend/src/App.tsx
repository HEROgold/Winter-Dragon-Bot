import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Container } from "./components/container";
import "./index.css";

import logo from "./logo.svg";
import reactLogo from "./react.svg";

export function App() {
  return (
    <BrowserRouter>
    <NavBar />
    <div className="app">
      <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/admin" element={<ViewUserTable />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
    </div>
    </BrowserRouter>
  );
}

export default App;
