import { useState } from "react";
import { useAuth } from "../contexts/auth-context";

export default function Home() {
  const { user, logout } = useAuth();
  const [leaving, setLeaving] = useState(false);

  if (!user) return null;

  async function handleLogout() {
    setLeaving(true);
    try {
      await logout();
    } finally {
      setLeaving(false);
    }
  }

  return (
    <main className="authenticated-screen">
      <section className="authenticated-card">
        <p className="authenticated-eyebrow">Sessão autenticada</p>
        <h1>Olá, {user.name}</h1>
        <p>{user.email}</p>
        <button type="button" onClick={handleLogout} disabled={leaving}>
          {leaving ? "Saindo…" : "Sair"}
        </button>
      </section>
    </main>
  );
}
