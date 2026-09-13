import { useNavigate } from "react-router-dom";
import RegisterForm from "../components/CadastroForm/CadastroForm";
import { cadastrar } from "../services/api";

export default function Cadastro() {
  const navigate = useNavigate();

  async function handleCadastro(nome: string, email: string, senha: string) {
    await cadastrar(nome, email, senha);
    navigate("/login");
  }

  return <RegisterForm onSubmit={handleCadastro} />;
}