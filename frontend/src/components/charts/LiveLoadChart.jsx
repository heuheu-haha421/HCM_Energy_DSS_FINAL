import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useLiveStore } from '../../store/liveStore';

function formatEnergy(kwh) {
    if (kwh == null || Number.isNaN(Number(kwh))) return '--';
    if (Math.abs(kwh) >= 1e9) return `${(kwh / 1e9).toFixed(2)} TWh`;
    if (Math.abs(kwh) >= 1e6) return `${(kwh / 1e6).toFixed(1)} GWh`;
    if (Math.abs(kwh) >= 1e3) return `${(kwh / 1e3).toFixed(0)} MWh`;
    return `${Number(kwh).toFixed(0)} kWh`;
}

function formatTemperature(value) {
    if (value == null || Number.isNaN(Number(value))) return '--';
    return `${Number(value).toFixed(1)}°C`;
}

function ChartTooltip({ active, payload, label }) {
    if (!active || !payload?.length) return null;

    return (
        <div style={{
            background: 'var(--bg-overlay)',
            border: '1px solid var(--border-normal)',
            borderRadius: 6,
            padding: '10px 12px',
            boxShadow: '0 10px 24px rgba(0,0,0,0.25)',
            minWidth: 170,
        }}>
            <div style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 8 }}>
                {label}
            </div>
            {payload.map(item => (
                <div key={item.dataKey} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 16,
                    fontSize: 11,
                    marginBottom: 4,
                    color: 'var(--text-secondary)',
                }}>
                    <span style={{ color: item.color }}>{item.name}</span>
                    <span style={{ color: 'var(--text-primary)' }}>
                        {item.dataKey === 'simulated_temp' ? formatTemperature(item.value) : formatEnergy(item.value)}
                    </span>
                </div>
            ))}
        </div>
    );
}

function LiveLoadChart() {
    const { livePoints } = useLiveStore();
    const latest = livePoints[livePoints.length - 1];
    const [isExpanded, setIsExpanded] = useState(false);

    return (
        <>
        <div style={{
            width: '100%',
            minHeight: 0,
            background: 'var(--bg-raised)',
            border: '1px solid var(--border-normal)',
            borderRadius: 8,
            padding: 16,
            marginBottom: 0,
        }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                gap: 12,
                marginBottom: 12,
            }}>
                <div>
                    <div style={{
                        fontSize: 16,
                        color: '#f8fafc',
                        fontWeight: 900,
                        marginBottom: 3,
                    }}>
                        LIVE FORECAST STREAM
                    </div>
                    <div style={{
                        color: 'var(--text-primary)',
                        fontSize: 14,
                        fontWeight: 700,
                    }}>
                        Forecast stream
                    </div>
                    {latest && (
                        <div style={{ fontSize: 14, color: '#cbd5e1', marginTop: 5 }}>
                            Week {latest.week ?? '--'} · Temp {formatTemperature(latest.simulated_temp)}
                        </div>
                    )}
                </div>

                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div style={{ fontSize: 14, color: '#cbd5e1', marginBottom: 3, fontWeight: 700 }}>LATEST</div>
                    <div style={{
                        color: 'var(--text-accent)',
                        fontFamily: 'var(--font-display)',
                        fontSize: 28,
                        fontWeight: 700,
                    }}>
                        {formatEnergy(latest?.predicted_load)}
                    </div>
                </div>
            </div>

            <ChartBody livePoints={livePoints} height={220} />

            <button
                className="btn"
                type="button"
                onClick={() => setIsExpanded(true)}
                style={{
                    width: '100%',
                    marginTop: 12,
                    fontSize: 10,
                    letterSpacing: '0.1em',
                }}
            >
                VIEW FULL CHART
            </button>
        </div>

        {isExpanded && (
            <div
                role="dialog"
                aria-modal="true"
                style={{
                    position: 'fixed',
                    inset: 0,
                    zIndex: 3000,
                    background: 'rgba(8,11,15,0.82)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: 24,
                }}
                onClick={() => setIsExpanded(false)}
            >
                <div
                    style={{
                        width: 'min(1120px, 96vw)',
                        height: 'min(720px, 88vh)',
                        background: 'var(--bg-surface)',
                        border: '1px solid var(--border-bright)',
                        borderRadius: 8,
                        padding: 20,
                        display: 'flex',
                        flexDirection: 'column',
                        boxShadow: '0 24px 80px rgba(0,0,0,0.45)',
                    }}
                    onClick={e => e.stopPropagation()}
                >
                    <div style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        justifyContent: 'space-between',
                        gap: 16,
                        marginBottom: 16,
                    }}>
                        <div>
                            <div style={{
                                fontSize: 10,
                                color: 'var(--text-dim)',
                                letterSpacing: '0.12em',
                                marginBottom: 4,
                            }}>
                                LIVE FORECAST STREAM
                            </div>
                            <div style={{
                                fontFamily: 'var(--font-display)',
                                fontSize: 24,
                                fontWeight: 700,
                                color: 'var(--text-primary)',
                            }}>
                                Forecast stream
                            </div>
                            {latest && (
                                <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 6 }}>
                                    Week {latest.week ?? '--'} · Temp {formatTemperature(latest.simulated_temp)}
                                </div>
                            )}
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                            <div style={{ textAlign: 'right' }}>
                                <div style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 3 }}>LATEST</div>
                                <div style={{
                                    color: 'var(--text-accent)',
                                    fontFamily: 'var(--font-display)',
                                    fontSize: 24,
                                    fontWeight: 700,
                                }}>
                                    {formatEnergy(latest?.predicted_load)}
                                </div>
                            </div>
                            <button
                                className="btn"
                                type="button"
                                onClick={() => setIsExpanded(false)}
                                style={{ fontSize: 11 }}
                            >
                                CLOSE
                            </button>
                        </div>
                    </div>

                    <div style={{ flex: 1, minHeight: 0 }}>
                        <ChartBody livePoints={livePoints} height="100%" expanded />
                    </div>
                </div>
            </div>
        )}
        </>
    );
}

function ChartBody({ livePoints, height, expanded = false }) {
    return (
        <div style={{ width: '100%', height }}>
                {livePoints.length === 0 ? (
                    <div style={{
                        height: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--text-dim)',
                        fontSize: 11,
                        border: '1px dashed var(--border-normal)',
                        borderRadius: 6,
                    }}>
                        Waiting for live data
                    </div>
                ) : (
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={livePoints} margin={{
                            top: expanded ? 12 : 8,
                            right: expanded ? 24 : 8,
                            bottom: expanded ? 12 : 0,
                            left: expanded ? 12 : 0,
                        }}>
                            <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                            <XAxis
                                dataKey="time"
                                tick={{ fontSize: expanded ? 12 : 10, fill: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}
                                tickLine={false}
                                axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
                                minTickGap={expanded ? 28 : 18}
                            />
                            <YAxis
                                yAxisId={0}
                                width={expanded ? 82 : 58}
                                domain={['dataMin', 'dataMax']}
                                tick={{ fontSize: expanded ? 12 : 10, fill: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}
                                tickFormatter={formatEnergy}
                                tickLine={false}
                                axisLine={false}
                            />
                            <YAxis
                                yAxisId={1}
                                orientation="right"
                                hide
                                domain={['dataMin', 'dataMax']}
                            />
                            <Tooltip content={<ChartTooltip />} />
                            <Legend
                                verticalAlign="top"
                                align="left"
                                height={24}
                                iconType="line"
                                wrapperStyle={{
                                    color: 'var(--text-secondary)',
                                    fontSize: expanded ? 12 : 10,
                                    fontFamily: 'var(--font-mono)',
                                }}
                            />
                            <Line
                                type="monotone"
                                dataKey="predicted_load"
                                name="Forecast"
                                yAxisId={0}
                                stroke="var(--text-accent)"
                                strokeWidth={2.5}
                                dot={false}
                                activeDot={{ r: 4, strokeWidth: 0 }}
                            />
                            <Line
                                type="monotone"
                                dataKey="simulated_temp"
                                name="Temperature"
                                stroke="var(--risk-med)"
                                strokeWidth={2}
                                dot={false}
                                yAxisId={1}
                                connectNulls
                            />
                        </LineChart>
                    </ResponsiveContainer>
                )}
            </div>
    );
}

export default LiveLoadChart;
