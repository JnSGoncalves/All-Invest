const paths = {
  grid: <><rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/></>,
  wallet: <><rect x="3" y="6" width="18" height="14" rx="2.5"/><path d="M3 9h18M16 14h.01M7 6V4.5A1.5 1.5 0 0 1 8.5 3H19"/></>,
  chart: <><path d="M4 19V5M4 19h17"/><path d="m7 15 4-4 3 2 6-7"/><path d="M16.5 6H20v3.5"/></>,
  plus: <><path d="M12 5v14M5 12h14"/></>,
  minus: <><path d="M5 12h14"/></>,
  arrow: <><path d="M5 12h14M13 6l6 6-6 6"/></>,
  logout: <><path d="M10 17l5-5-5-5M15 12H3"/><path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6"/></>,
  trash: <><path d="M4 7h16M10 11v6M14 11v6M5 7l1 13h12l1-13M9 7V4h6v3"/></>,
  check: <><path d="m5 12.5 4.5 4.5L19 7.5"/></>,
  alert: <><circle cx="12" cy="12" r="9"/><path d="M12 7.5v5.5M12 16.5h.01"/></>,
  info: <><circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.5h.01"/></>,
  close: <><path d="M6 6l12 12M18 6 6 18"/></>,
  search: <><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/></>,
  folder: <><path d="M3.5 7.5A2 2 0 0 1 5.5 5.5h4l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2Z"/></>,
  pie: <><path d="M12 3.5a8.5 8.5 0 1 0 8.5 8.5H12Z"/><path d="M15 3.8A8.5 8.5 0 0 1 20.2 9H15Z"/></>,
  layers: <><path d="m12 4 8.5 4.5L12 13 3.5 8.5Z"/><path d="m3.5 12.5 8.5 4.5 8.5-4.5M3.5 16.5 12 21l8.5-4.5"/></>,
  trend: <><path d="m3.5 16.5 6-6 4 4 7-7.5"/><path d="M15.5 7h5v5"/></>,
  up: <><path d="M12 19V5M6 11l6-6 6 6"/></>,
  down: <><path d="M12 5v14M6 13l6 6 6-6"/></>,
};

export type IconName = keyof typeof paths;

export default function Icon({ name, size = 19 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}
