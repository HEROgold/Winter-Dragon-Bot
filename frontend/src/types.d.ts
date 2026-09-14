declare const Bun: {
  build(options: unknown): Promise<{ success: boolean }>;
  file(path: string | URL): { text(): Promise<string> };
  write(path: string | URL, data: string | Blob): Promise<number>;
  serve(options: {
    port: number;
    fetch(request: Request): Response | Promise<Response>;
  }): void;
};

declare const process: {
  env: Record<string, string | undefined>;
};

declare module "react" {
  export function useState<T>(
    initialState: T | (() => T),
  ): [T, (value: T | ((current: T) => T)) => void];
  export function useEffect(
    effect: () => void | (() => void),
    deps?: unknown[],
  ): void;
}

declare module "react-dom/client" {
  export function createRoot(container: Element | DocumentFragment): {
    render(node: unknown): void;
  };
}

interface TournamentPlayer {
  name: string;
  intendedPick: string;
}

interface TournamentTeam {
  players: TournamentPlayer[];
}

interface TournamentSnapshot {
  guildId: number;
  status: string;
  teams: TournamentTeam[];
}

declare module "*.tsrx" {
  export const App: unknown;
  export const Dashboard: unknown;
  export const TournamentPanel: unknown;
  export default App;
}

declare namespace JSX {
  interface IntrinsicElements {
    [elementName: string]: any;
  }
}
