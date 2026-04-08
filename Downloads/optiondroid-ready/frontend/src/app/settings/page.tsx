"use client";

import { useState, useEffect } from "react";
import { Check } from "lucide-react";

interface AppSettings {
  defaultTicker: string;
  autoRefreshInterval: number;
  minOIFilter: number;
  minVolumeFilter: number;
  showGreeks: boolean;
}

const DEFAULTS: AppSettings = {
  defaultTicker: "SPY",
  autoRefreshInterval: 60,
  minOIFilter: 0,
  minVolumeFilter: 0,
  showGreeks: false,
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings>(DEFAULTS);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("options_settings");
    if (stored) {
      try { setSettings({ ...DEFAULTS, ...JSON.parse(stored) }); } catch {}
    }
  }, []);

  const save = () => {
    localStorage.setItem("options_settings", JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const set = (key: keyof AppSettings, value: any) =>
    setSettings(prev => ({ ...prev, [key]: value }));

  return (
    <div className="max-w-lg space-y-6 animate-fade-in">
      <div>
        <h1 className="text-xl font-semibold">Settings</h1>
        <p className="text-sm text-text-muted">Configure default app behavior</p>
      </div>

      <div className="card space-y-5">
        <h2 className="text-sm font-semibold text-text-primary border-b border-bg-border pb-2">
          General
        </h2>

        <div className="space-y-1">
          <label className="text-xs text-text-muted font-medium">Default Ticker</label>
          <input
            className="input w-32 uppercase font-mono"
            value={settings.defaultTicker}
            onChange={e => set("defaultTicker", e.target.value.toUpperCase())}
            maxLength={6}
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs text-text-muted font-medium">
            Auto-Refresh Interval (seconds)
          </label>
          <input
            type="number"
            className="input w-32 font-mono"
            value={settings.autoRefreshInterval}
            min={15}
            max={300}
            onChange={e => set("autoRefreshInterval", Number(e.target.value))}
          />
        </div>
      </div>

      <div className="card space-y-5">
        <h2 className="text-sm font-semibold text-text-primary border-b border-bg-border pb-2">
          Default Filters
        </h2>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="text-xs text-text-muted font-medium">Min OI</label>
            <input
              type="number"
              className="input w-full font-mono"
              value={settings.minOIFilter}
              min={0}
              onChange={e => set("minOIFilter", Number(e.target.value))}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-text-muted font-medium">Min Volume</label>
            <input
              type="number"
              className="input w-full font-mono"
              value={settings.minVolumeFilter}
              min={0}
              onChange={e => set("minVolumeFilter", Number(e.target.value))}
            />
          </div>
        </div>
      </div>

      <div className="card space-y-5">
        <h2 className="text-sm font-semibold text-text-primary border-b border-bg-border pb-2">
          Display
        </h2>
        <label className="flex items-center gap-3 cursor-pointer">
          <div
            onClick={() => set("showGreeks", !settings.showGreeks)}
            className={`relative w-9 h-5 rounded-full transition-colors ${settings.showGreeks ? "bg-accent" : "bg-bg-border"}`}
          >
            <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${settings.showGreeks ? "translate-x-4" : "translate-x-0.5"}`} />
          </div>
          <span className="text-sm text-text-secondary">Show Greeks columns</span>
        </label>
      </div>

      <div className="card space-y-3">
        <h2 className="text-sm font-semibold text-text-primary border-b border-bg-border pb-2">
          Data Source
        </h2>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-success animate-pulse-fast" />
          <span className="text-sm text-text-secondary">Robinhood (via robin_stocks)</span>
        </div>
        <p className="text-xs text-text-muted">
          Provider is configured in the backend <code className="text-text-secondary bg-bg-raised px-1 py-0.5 rounded">.env</code> file.
          Change <code className="text-text-secondary bg-bg-raised px-1 py-0.5 rounded">DATA_PROVIDER</code> to switch providers.
        </p>
      </div>

      {/* Save */}
      <button onClick={save} className="btn-primary flex items-center gap-2">
        {saved ? <Check className="w-4 h-4" /> : null}
        {saved ? "Saved!" : "Save Settings"}
      </button>
    </div>
  );
}
