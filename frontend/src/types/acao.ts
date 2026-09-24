export interface Acao {
  id: string;
  nomeAtivo: string;
  quantidade: number;
  corretora: string;
}

export type AcaoResponse = Acao;