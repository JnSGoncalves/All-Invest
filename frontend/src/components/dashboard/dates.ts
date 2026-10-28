// Datas da API vêm como "AAAA-MM-DD"; new Date(string) as trataria como UTC
// e, no fuso de Brasília, mostraria o dia anterior.
export function parseDay(day: string): Date {
  const [year, month, date] = day.split("-").map(Number);
  return new Date(year, month - 1, date);
}
