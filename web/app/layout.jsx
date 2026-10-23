import "./globals.css";

export const metadata = {
  title: "MÉLODIA — Studio de création musicale",
  description: "Composez vos propres chansons depuis votre navigateur.",
  applicationName: "MÉLODIA",
};

export default function RootLayout({ children }) {
  return <html lang="fr"><body>{children}</body></html>;
}
