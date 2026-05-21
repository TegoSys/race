import React, { useEffect, useState } from 'react';
import apiClient from '../lib/api';
import { Card } from '../components/ui/Card';

interface Rule {
  id: string;
  name: string;
  description: string;
  config_key: string;
  thresholds: Record<string, unknown>;
}

export const Rules: React.FC = () => {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedThresholds, setEditedThresholds] = useState<Record<string, Record<string, string>>>({});
  const [validationErrors, setValidationErrors] = useState<Record<string, Record<string, boolean>>>({});
  const [saving, setSaving] = useState(false);
  const [restoring, setRestoring] = useState(false);

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      const res = await apiClient.get<Rule[]>('/rules');
      setRules(res.data);
      buildEditableThresholds(res.data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch rules');
    } finally {
      setLoading(false);
    }
  };

  const buildEditableThresholds = (ruleList: Rule[]) => {
    const thresholds: Record<string, Record<string, string>> = {};
    ruleList.forEach(rule => {
      thresholds[rule.id] = {};
      Object.entries(rule.thresholds).forEach(([key, value]) => {
        thresholds[rule.id][key] = String(value);
      });
    });
    setEditedThresholds(thresholds);
    setValidationErrors({});
  };

  const handleThresholdChange = (ruleId: string, key: string, value: string) => {
    setEditedThresholds(prev => ({
      ...prev,
      [ruleId]: { ...prev[ruleId], [key]: value },
    }));
    // Clear validation error for this field
    setValidationErrors(prev => ({
      ...prev,
      [ruleId]: { ...(prev[ruleId] || {}), [key]: false },
    }));
  };

  const validateAllThresholds = (): boolean => {
    const errors: Record<string, Record<string, boolean>> = {};
    let hasErrors = false;

    Object.entries(editedThresholds).forEach(([ruleId, thresholds]) => {
      errors[ruleId] = {};
      Object.entries(thresholds).forEach(([key, value]) => {
        const isValid = value.trim() !== '' && !isNaN(Number(value));
        errors[ruleId][key] = !isValid;
        if (!isValid) hasErrors = true;
      });
    });

    setValidationErrors(errors);
    return !hasErrors;
  };

  const handleSave = async () => {
    if (!validateAllThresholds()) return;

    setSaving(true);
    try {
      // Build the config structure: { rule_section: { threshold_key: value } }
      const config: Record<string, Record<string, number>> = {};
      rules.forEach(rule => {
        const ruleThresholds: Record<string, number> = {};
        Object.entries(editedThresholds[rule.id] || {}).forEach(([key, value]) => {
          const num = Number(value);
          ruleThresholds[key] = isNaN(num) ? 0 : num;
        });
        // Use the config_key (snake_case) from the backend
        config[rule.config_key] = ruleThresholds;
      });

      await apiClient.post('/rules/config', config);
      setIsEditing(false);
      await fetchRules();
    } catch (err: any) {
      setError(err.message || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleRestoreDefaults = async () => {
    setRestoring(true);
    try {
      const res = await apiClient.get<Record<string, Record<string, number>>>('/rules/config/defaults');
      buildEditableThresholdsFromConfig(res.data);
    } catch (err: any) {
      setError(err.message || 'Failed to restore defaults');
    } finally {
      setRestoring(false);
    }
  };

  const buildEditableThresholdsFromConfig = (config: Record<string, Record<string, number>>) => {
    const thresholds: Record<string, Record<string, string>> = {};
    rules.forEach(rule => {
      thresholds[rule.id] = {};
      const ruleConfig = config[rule.config_key];
      if (ruleConfig) {
        Object.entries(ruleConfig).forEach(([key, value]) => {
          thresholds[rule.id][key] = String(value);
        });
      } else {
        // Fallback to current thresholds
        Object.entries(rule.thresholds).forEach(([key, value]) => {
          thresholds[rule.id][key] = String(value);
        });
      }
    });
    setEditedThresholds(thresholds);
    setValidationErrors({});
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        Loading configured rules...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-red-400">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <h2 className="text-3xl font-bold leading-normal bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
          Configured Rules
        </h2>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRestoreDefaults}
            disabled={restoring || !isEditing}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg transition-colors text-sm font-medium flex items-center gap-2"
          >
            {restoring && <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
            {restoring ? 'Restoring...' : 'Restore Defaults'}
          </button>
          <button
            onClick={isEditing ? handleSave : () => setIsEditing(true)}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 text-white rounded-lg transition-colors text-sm font-medium flex items-center gap-2"
          >
            {saving && <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
            {saving ? 'Saving...' : isEditing ? 'Save' : 'Edit'}
          </button>
        </div>
      </div>
      <div className="space-y-4">
        {rules.map((rule) => (
          <Card key={rule.id} variant="glass" className="p-6">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-lg font-semibold text-white">{rule.name}</h3>
                  <span className="text-xs font-mono text-slate-400 bg-white/5 px-2 py-0.5 rounded">
                    {rule.id}
                  </span>
                </div>
                <p className="text-slate-400 text-sm">{rule.description}</p>
              </div>
            </div>
            {Object.keys(rule.thresholds).length > 0 && (
              <div className="mt-4 pt-4 border-t border-white/10">
                {isEditing ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {Object.entries(editedThresholds[rule.id] || {}).map(([key, value]) => (
                      <div key={key} className="flex flex-col gap-1">
                        <label className="text-xs font-mono text-slate-500 uppercase">{key}</label>
                        <input
                          type="text"
                          value={value}
                          onChange={(e) => handleThresholdChange(rule.id, key, e.target.value)}
                          className={`bg-slate-800/50 border rounded-lg px-3 py-2 text-white outline-none focus:ring-2 ring-blue-500/50 font-mono text-sm ${
                            validationErrors[rule.id]?.[key]
                              ? 'border-red-500/50'
                              : 'border-white/10'
                          }`}
                        />
                        {validationErrors[rule.id]?.[key] && (
                          <span className="text-xs text-red-400">Must be a valid number</span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-x-6 gap-y-2">
                    {Object.entries(rule.thresholds).map(([key, value]) => (
                      <div key={key} className="flex items-center gap-2">
                        <span className="text-xs font-mono text-slate-500 uppercase">{key}</span>
                        <span className="text-sm font-medium text-slate-300">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </Card>
        ))}
        {rules.length === 0 && (
          <Card variant="glass" className="p-12 text-center text-slate-500">
            No rules configured in the engine.
          </Card>
        )}
      </div>
      <p className="mt-6 text-slate-500 text-sm italic">
        These rules are used by the backend engine to detect anomalies and violations in race telemetry.
        Thresholds are configured in <code className="text-slate-400">rules_config.yaml</code>.
      </p>
    </div>
  );
};
