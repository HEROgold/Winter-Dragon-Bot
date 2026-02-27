// Base page which contains the common elements of all pages, such as the header and footer.

import { Body } from "./Body";
import { Footer } from "./Footer";
import { Header } from "./Header";

export default function Base({ children }: { children: React.ReactNode }) {
  return (
    <div className="app">
      <Header />
      <Body>{children}</Body>
      <Footer />
    </div>
  );
}
