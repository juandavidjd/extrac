"use client";

interface Notification {
  event_type: string;
  timestamp: string;
  data?: any;
  ttl_ms?: number;
}

interface Props {
  notifications: Notification[];
}

const TOAST_STYLES: Record<string, { border: string; icon: string }> = {
  order_paid: { border: "border-emerald-500/50", icon: "💚" },
  fitment_critical: { border: "border-amber-500/50", icon: "⚠" },
  guardian_alert: { border: "border-red-500/50", icon: "🛡" },
};

export default function EphemeralToast({ notifications }: Props) {
  if (!notifications.length) return null;

  return (
    <div className="fixed top-16 right-4 z-50 space-y-2 max-w-xs">
      {notifications.slice(0, 2).map((notif, i) => {
        const style = TOAST_STYLES[notif.event_type] || {
          border: "border-neutral-500/50",
          icon: "📡",
        };

        return (
          <div
            key={i}
            className={`bg-neutral-900/90 backdrop-blur border ${style.border} rounded-lg px-4 py-3 text-sm text-neutral-200 animate-[fadeIn_0.3s_ease-out]`}
          >
            <span className="mr-2">{style.icon}</span>
            {notif.data?.message ||
              notif.data?.summary ||
              notif.event_type.replace(/_/g, " ")}
          </div>
        );
      })}
    </div>
  );
}
