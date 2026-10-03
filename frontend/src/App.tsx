import Login from "./pages/Login";
import GoogleCallback from "./pages/GoogleCallback";
import Home from "./pages/Home";
import { AuthProvider } from "./contexts/AuthContext";
import { useAuth } from "./contexts/auth-context";
import "./App.css";

function AuthenticatedApp() {
  const { user, loading, sessionError, retrySession } = useAuth();

  if (loading) {
    return (
      <main className="auth-status-screen">
        <div className="auth-spinner" aria-label="Carregando sessão" />
      </main>
    );
  }

  if (sessionError) {
    return (
      <main className="auth-status-screen">
        <section className="auth-status-card" role="alert">
          <h1>Não foi possível acessar sua conta</h1>
          <p>{sessionError}</p>
          <button type="button" className="primary-button" onClick={retrySession}>Tentar novamente</button>
        </section>
      </main>
    );
  }

  return user ? <Home key={user.user_id} /> : <Login />;
}

function App() {
  if (window.location.pathname === "/auth/callback") {
    return <GoogleCallback />;
  }

  return (
    <AuthProvider>
      <AuthenticatedApp />
    </AuthProvider>
  );
}

export default App;
