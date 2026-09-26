import { useEffect, useRef, useState } from "react";
import { completeGoogleLogin } from "../services/api";

export default function GoogleCallback() {
  const started = useRef(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    completeGoogleLogin()
      .then(() => window.location.replace("/"))
      .catch((reason: unknown) => {
        setError(
          reason instanceof Error
            ? reason.message
            : "Não foi possível concluir o login com Google.",
        );
      });
  }, []);

  return (
    <main className="auth-status-screen">
      <section className="auth-status-card" aria-live="polite">
        {error ? (
          <>
            <h1>Não foi possível entrar</h1>
            <p role="alert">{error}</p>
            <a href="/">Voltar para o login</a>
          </>
        ) : (
          <>
            <div className="auth-spinner" aria-hidden="true" />
            <h1>Concluindo seu login</h1>
            <p>Estamos validando sua conta com segurança.</p>
          </>
        )}
      </section>
    </main>
  );
}
