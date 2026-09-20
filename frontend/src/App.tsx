import Login from "./pages/Login";
import GoogleCallback from "./pages/GoogleCallback";
import Home from "./pages/Home";
import { AuthProvider } from "./contexts/AuthContext";
import { useAuth } from "./contexts/auth-context";
import "./App.css";

function AuthenticatedApp() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <main className="auth-status-screen">
        <div className="auth-spinner" aria-label="Carregando sessão" />
      </main>
    );
  }

  return user ? <Home /> : <Login />;
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
