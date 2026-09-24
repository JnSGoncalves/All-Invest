import { useNavigate } from "react-router-dom";
import CadastroAcaoForm from "../components/CadastroAcaoForm/CadastroAcaoForm";
import { cadastrarAcao } from "../services/api";

export default function CadastroAcao() {
  const navigate = useNavigate();

  async function handleCadastro(nomeAtivo: string, quantidade: number, corretora: string) {
    await cadastrarAcao(nomeAtivo, quantidade, corretora);
    navigate("/acoes"); // ajuste para a rota real da listagem quando ela existir
  }

  return <CadastroAcaoForm onSubmit={handleCadastro} />;
}
