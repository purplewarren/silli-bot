from datetime import datetime, timedelta
from collections import Counter
from typing import List, Dict
from .models import EventRecord

def compute_insights(events: List[EventRecord]) -> Dict[str, str]:
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    # Filter to last 7 days
    events = [e for e in events if hasattr(e, 'ts') and e.ts >= week_ago]
    out = {}

    # Night
    night_scores = []
    night_badge_hits = 0
    night_total = 0
    night_rationales = []
    for e in events:
        if e.labels and any(l == 'dyad:night' for l in e.labels):
            if e.score is not None:
                night_scores.append(e.score)
            if e.labels and any(b in e.labels for b in ['Speech', 'Fluctuating']):
                night_badge_hits += 1
            night_total += 1
            # Collect rationales from reasoning context
            if e.context and e.context.get('reasoning', {}).get('rationale'):
                night_rationales.append(e.context['reasoning']['rationale'])
    
    if night_scores:
        avg_score = round(sum(night_scores) / len(night_scores))
        pct_badge = int(100 * night_badge_hits / night_total) if night_total else 0
        insight = f"Avg wind-down {avg_score}/100; {pct_badge}% sessions with speech/fluctuating"
        
        # Add rationale if available
        if night_rationales:
            # Take the most recent rationale and truncate if needed
            latest_rationale = night_rationales[-1]
            if len(latest_rationale) > 100:
                latest_rationale = latest_rationale[:97] + "..."
            insight += f" • {latest_rationale}"
        
        out['night'] = insight
    else:
        out['night'] = "—"

    # Tantrum
    tan_esc = []
    triggers = []
    tantrum_rationales = []
    for e in events:
        if e.labels and any(l == 'dyad:tantrum' for l in e.labels):
            if e.metrics and e.metrics.get('escalation_index') is not None:
                tan_esc.append(e.metrics['escalation_index'])
            if e.context and e.context.get('trigger'):
                triggers.append(e.context['trigger'])
            # Collect rationales from reasoning context
            if e.context and e.context.get('reasoning', {}).get('rationale'):
                tantrum_rationales.append(e.context['reasoning']['rationale'])
    
    if tan_esc:
        avg_esc = sum(tan_esc) / len(tan_esc)
        most_common_trigger = Counter(triggers).most_common(1)[0][0] if triggers else '—'
        insight = f"Avg escalation {avg_esc:.2f}; common trigger: {most_common_trigger}"
        
        # Add rationale if available
        if tantrum_rationales:
            # Take the most recent rationale and truncate if needed
            latest_rationale = tantrum_rationales[-1]
            if len(latest_rationale) > 100:
                latest_rationale = latest_rationale[:97] + "..."
            insight += f" • {latest_rationale}"
        
        out['tantrum'] = insight
    else:
        out['tantrum'] = "—"

    # Meal
    meal_moods = []
    eaten_pcts = []
    meal_rationales = []
    for e in events:
        if e.labels and any(l == 'dyad:meal' for l in e.labels):
            if e.metrics and e.metrics.get('meal_mood') is not None:
                meal_moods.append(e.metrics['meal_mood'])
            if e.context and e.context.get('eaten_pct') is not None:
                eaten_pcts.append(e.context['eaten_pct'])
            # Collect rationales from reasoning context
            if e.context and e.context.get('reasoning', {}).get('rationale'):
                meal_rationales.append(e.context['reasoning']['rationale'])
    
    if meal_moods:
        avg_mood = round(sum(meal_moods) / len(meal_moods))
        avg_eaten = round(sum(eaten_pcts) / len(eaten_pcts)) if eaten_pcts else '—'
        insight = f"Avg meal mood {avg_mood}/100; eaten {avg_eaten}%"
        
        # Add rationale if available
        if meal_rationales:
            # Take the most recent rationale and truncate if needed
            latest_rationale = meal_rationales[-1]
            if len(latest_rationale) > 100:
                latest_rationale = latest_rationale[:97] + "..."
            insight += f" • {latest_rationale}"
        
        out['meal'] = insight
    else:
        out['meal'] = "—"

    return out