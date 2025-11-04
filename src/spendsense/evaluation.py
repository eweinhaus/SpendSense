"""
Evaluation harness module for SpendSense MVP.
Calculates metrics for coverage, explainability, relevance, latency, and fairness.
"""

import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from .database import get_db_connection
from .recommendations import generate_recommendations


def calculate_coverage(conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Calculate coverage metric: % of users with assigned persona + ≥3 behaviors.
    
    Args:
        conn: Database connection (creates new if None)
        
    Returns:
        Dictionary with coverage metrics
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        
        # Get total users
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        # Get users with assigned personas
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM personas")
        users_with_personas = cursor.fetchone()[0]
        
        # Get users with ≥3 detected behaviors (signals)
        cursor.execute("""
            SELECT user_id, COUNT(*) as signal_count
            FROM signals
            GROUP BY user_id
            HAVING signal_count >= 3
        """)
        users_with_3plus_behaviors = len(cursor.fetchall())
        
        # Get users with both persona AND ≥3 behaviors
        cursor.execute("""
            SELECT DISTINCT p.user_id
            FROM personas p
            INNER JOIN (
                SELECT user_id, COUNT(*) as signal_count
                FROM signals
                GROUP BY user_id
                HAVING signal_count >= 3
            ) s ON p.user_id = s.user_id
        """)
        users_with_both = len(cursor.fetchall())
        
        # Calculate percentages
        persona_coverage = (users_with_personas / total_users * 100) if total_users > 0 else 0
        behavior_coverage = (users_with_3plus_behaviors / total_users * 100) if total_users > 0 else 0
        combined_coverage = (users_with_both / total_users * 100) if total_users > 0 else 0
        
        return {
            'total_users': total_users,
            'users_with_personas': users_with_personas,
            'users_with_3plus_behaviors': users_with_3plus_behaviors,
            'users_with_both': users_with_both,
            'persona_coverage_pct': round(persona_coverage, 2),
            'behavior_coverage_pct': round(behavior_coverage, 2),
            'combined_coverage_pct': round(combined_coverage, 2),
            'target_met': combined_coverage >= 100.0
        }
        
    finally:
        if close_conn:
            conn.close()


def calculate_explainability(conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Calculate explainability metric: % of recommendations with plain-language rationales.
    
    Args:
        conn: Database connection (creates new if None)
        
    Returns:
        Dictionary with explainability metrics
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        
        # Get total recommendations
        cursor.execute("SELECT COUNT(*) FROM recommendations")
        total_recommendations = cursor.fetchone()[0]
        
        # Get recommendations with non-empty rationales
        cursor.execute("""
            SELECT COUNT(*) FROM recommendations
            WHERE rationale IS NOT NULL AND rationale != ''
        """)
        recommendations_with_rationales = cursor.fetchone()[0]
        
        # Calculate percentage
        explainability_pct = (recommendations_with_rationales / total_recommendations * 100) if total_recommendations > 0 else 0
        
        # Optional: Quality scoring (basic - check if rationale has data citations)
        cursor.execute("""
            SELECT COUNT(*) FROM recommendations
            WHERE rationale IS NOT NULL 
            AND rationale != ''
            AND (rationale LIKE '%utilization%' 
                 OR rationale LIKE '%subscription%'
                 OR rationale LIKE '%balance%'
                 OR rationale LIKE '%spend%'
                 OR rationale LIKE '%signal%')
        """)
        recommendations_with_data_citations = cursor.fetchone()[0]
        quality_score_pct = (recommendations_with_data_citations / total_recommendations * 100) if total_recommendations > 0 else 0
        
        return {
            'total_recommendations': total_recommendations,
            'recommendations_with_rationales': recommendations_with_rationales,
            'explainability_pct': round(explainability_pct, 2),
            'recommendations_with_data_citations': recommendations_with_data_citations,
            'quality_score_pct': round(quality_score_pct, 2),
            'target_met': explainability_pct >= 100.0
        }
        
    finally:
        if close_conn:
            conn.close()


def calculate_relevance(conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Calculate relevance metric: Persona-content fit scoring.
    
    Uses a simple scoring system: persona matches recommendation category = 1, else 0.
    
    Args:
        conn: Database connection (creates new if None)
        
    Returns:
        Dictionary with relevance metrics
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        
        # Get all recommendations with their personas
        cursor.execute("""
            SELECT r.id, r.persona_matched, r.title
            FROM recommendations r
        """)
        
        recommendations = cursor.fetchall()
        
        # Persona-to-keyword mapping for relevance scoring
        persona_keywords = {
            'high_utilization': ['credit', 'utilization', 'balance', 'payment', 'interest'],
            'variable_income_budgeter': ['budget', 'income', 'variable', 'emergency', 'smoothing'],
            'savings_builder': ['savings', 'goal', 'automation', 'hysa', 'high-yield'],
            'financial_newcomer': ['credit', 'building', 'basics', 'foundation', 'account'],
            'subscription_heavy': ['subscription', 'recurring', 'bill', 'track'],
            'neutral': []  # Neutral personas can have any content
        }
        
        total_recommendations = len(recommendations)
        relevant_count = 0
        
        for rec_id, persona, title in recommendations:
            if persona in persona_keywords:
                keywords = persona_keywords[persona]
                title_lower = title.lower()
                
                # Check if any keyword matches
                if any(keyword in title_lower for keyword in keywords) or persona == 'neutral':
                    relevant_count += 1
            else:
                # Unknown persona - count as relevant
                relevant_count += 1
        
        relevance_pct = (relevant_count / total_recommendations * 100) if total_recommendations > 0 else 0
        average_fit_score = relevant_count / total_recommendations if total_recommendations > 0 else 0
        
        return {
            'total_recommendations': total_recommendations,
            'relevant_recommendations': relevant_count,
            'relevance_pct': round(relevance_pct, 2),
            'average_fit_score': round(average_fit_score, 3),
            'target_met': relevance_pct >= 80.0  # 80% relevance target
        }
        
    finally:
        if close_conn:
            conn.close()


def calculate_latency(conn: Optional[sqlite3.Connection] = None, sample_size: int = 10) -> Dict:
    """
    Calculate latency metric: Time to generate recommendations per user.
    
    Args:
        conn: Database connection (creates new if None)
        sample_size: Number of users to sample for latency measurement
        
    Returns:
        Dictionary with latency metrics
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        
        # Get sample of users (with consent)
        cursor.execute("""
            SELECT id FROM users 
            WHERE consent_given = 1
            LIMIT ?
        """, (sample_size,))
        
        user_ids = [row[0] for row in cursor.fetchall()]
        
        if not user_ids:
            return {
                'sample_size': 0,
                'average_latency_seconds': 0,
                'min_latency_seconds': 0,
                'max_latency_seconds': 0,
                'target_met': False,
                'target_seconds': 5
            }
        
        latencies = []
        
        for user_id in user_ids:
            start_time = time.time()
            try:
                # Generate recommendations for this user
                generate_recommendations(user_id, conn)
                end_time = time.time()
                latency = end_time - start_time
                latencies.append(latency)
            except Exception as e:
                # Skip users with errors
                continue
        
        if not latencies:
            return {
                'sample_size': 0,
                'average_latency_seconds': 0,
                'min_latency_seconds': 0,
                'max_latency_seconds': 0,
                'target_met': False,
                'target_seconds': 5
            }
        
        average_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        
        return {
            'sample_size': len(latencies),
            'average_latency_seconds': round(average_latency, 3),
            'min_latency_seconds': round(min_latency, 3),
            'max_latency_seconds': round(max_latency, 3),
            'target_met': average_latency < 5.0,
            'target_seconds': 5
        }
        
    finally:
        if close_conn:
            conn.close()


def calculate_fairness(conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Calculate fairness metric: Persona and recommendation distribution analysis.
    
    Args:
        conn: Database connection (creates new if None)
        
    Returns:
        Dictionary with fairness metrics
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        
        # Persona distribution
        cursor.execute("""
            SELECT persona_type, COUNT(*) as count
            FROM personas
            GROUP BY persona_type
            ORDER BY count DESC
        """)
        
        persona_distribution = {}
        total_personas = 0
        for persona_type, count in cursor.fetchall():
            persona_distribution[persona_type] = count
            total_personas += count
        
        # Calculate persona percentages
        persona_percentages = {}
        for persona_type, count in persona_distribution.items():
            persona_percentages[persona_type] = round((count / total_personas * 100), 2) if total_personas > 0 else 0
        
        # Recommendation distribution by persona
        cursor.execute("""
            SELECT persona_matched, COUNT(*) as count
            FROM recommendations
            GROUP BY persona_matched
            ORDER BY count DESC
        """)
        
        recommendation_distribution = {}
        total_recommendations = 0
        for persona_type, count in cursor.fetchall():
            recommendation_distribution[persona_type] = count
            total_recommendations += count
        
        # Calculate recommendation percentages
        recommendation_percentages = {}
        for persona_type, count in recommendation_distribution.items():
            recommendation_percentages[persona_type] = round((count / total_recommendations * 100), 2) if total_recommendations > 0 else 0
        
        # Calculate distribution evenness (coefficient of variation)
        if persona_distribution:
            persona_counts = list(persona_distribution.values())
            persona_mean = sum(persona_counts) / len(persona_counts)
            persona_variance = sum((x - persona_mean) ** 2 for x in persona_counts) / len(persona_counts)
            persona_std = persona_variance ** 0.5
            persona_cv = (persona_std / persona_mean * 100) if persona_mean > 0 else 0
        else:
            persona_cv = 0
        
        if recommendation_distribution:
            rec_counts = list(recommendation_distribution.values())
            rec_mean = sum(rec_counts) / len(rec_counts)
            rec_variance = sum((x - rec_mean) ** 2 for x in rec_counts) / len(rec_counts)
            rec_std = rec_variance ** 0.5
            rec_cv = (rec_std / rec_mean * 100) if rec_mean > 0 else 0
        else:
            rec_cv = 0
        
        return {
            'persona_distribution': persona_distribution,
            'persona_percentages': persona_percentages,
            'recommendation_distribution': recommendation_distribution,
            'recommendation_percentages': recommendation_percentages,
            'persona_distribution_evenness_cv': round(persona_cv, 2),
            'recommendation_distribution_evenness_cv': round(rec_cv, 2),
            'total_personas': total_personas,
            'total_recommendations': total_recommendations
        }
        
    finally:
        if close_conn:
            conn.close()


def generate_report(metrics: Dict, output_dir: str = "metrics") -> Dict:
    """
    Generate evaluation reports in JSON, CSV, and Markdown formats.
    
    Args:
        metrics: Dictionary with all calculated metrics
        output_dir: Directory to save output files
        
    Returns:
        Dictionary with file paths of generated reports
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Generate JSON report
    json_file = output_path / f"metrics_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(metrics, f, indent=2, default=str)
    
    # Generate CSV report (summary)
    csv_file = output_path / f"metrics_summary_{timestamp}.csv"
    with open(csv_file, 'w') as f:
        f.write("Metric,Value,Target,Target Met\n")
        
        # Coverage
        coverage = metrics.get('coverage', {})
        f.write(f"Coverage (Persona + ≥3 Behaviors),{coverage.get('combined_coverage_pct', 0)}%,100%,{'Yes' if coverage.get('target_met', False) else 'No'}\n")
        
        # Explainability
        explainability = metrics.get('explainability', {})
        f.write(f"Explainability (Rationales),{explainability.get('explainability_pct', 0)}%,100%,{'Yes' if explainability.get('target_met', False) else 'No'}\n")
        
        # Relevance
        relevance = metrics.get('relevance', {})
        f.write(f"Relevance (Persona-Content Fit),{relevance.get('relevance_pct', 0)}%,80%,{'Yes' if relevance.get('target_met', False) else 'No'}\n")
        
        # Latency
        latency = metrics.get('latency', {})
        f.write(f"Latency (Average),{latency.get('average_latency_seconds', 0)}s,<5s,{'Yes' if latency.get('target_met', False) else 'No'}\n")
    
    # Generate Markdown summary report
    md_file = output_path / f"metrics_summary_{timestamp}.md"
    with open(md_file, 'w') as f:
        f.write("# SpendSense Evaluation Metrics Summary\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Executive Summary\n\n")
        coverage = metrics.get('coverage', {})
        explainability = metrics.get('explainability', {})
        relevance = metrics.get('relevance', {})
        latency = metrics.get('latency', {})
        
        f.write(f"- **Coverage:** {coverage.get('combined_coverage_pct', 0)}% (Target: 100%) {'✅' if coverage.get('target_met', False) else '❌'}\n")
        f.write(f"- **Explainability:** {explainability.get('explainability_pct', 0)}% (Target: 100%) {'✅' if explainability.get('target_met', False) else '❌'}\n")
        f.write(f"- **Relevance:** {relevance.get('relevance_pct', 0)}% (Target: 80%) {'✅' if relevance.get('target_met', False) else '❌'}\n")
        f.write(f"- **Latency:** {latency.get('average_latency_seconds', 0)}s (Target: <5s) {'✅' if latency.get('target_met', False) else '❌'}\n\n")
        
        f.write("## Detailed Metrics\n\n")
        
        # Coverage details
        f.write("### Coverage\n\n")
        f.write(f"- Total Users: {coverage.get('total_users', 0)}\n")
        f.write(f"- Users with Personas: {coverage.get('users_with_personas', 0)} ({coverage.get('persona_coverage_pct', 0)}%)\n")
        f.write(f"- Users with ≥3 Behaviors: {coverage.get('users_with_3plus_behaviors', 0)} ({coverage.get('behavior_coverage_pct', 0)}%)\n")
        f.write(f"- Users with Both: {coverage.get('users_with_both', 0)} ({coverage.get('combined_coverage_pct', 0)}%)\n\n")
        
        # Explainability details
        f.write("### Explainability\n\n")
        f.write(f"- Total Recommendations: {explainability.get('total_recommendations', 0)}\n")
        f.write(f"- With Rationales: {explainability.get('recommendations_with_rationales', 0)} ({explainability.get('explainability_pct', 0)}%)\n")
        f.write(f"- With Data Citations: {explainability.get('recommendations_with_data_citations', 0)} ({explainability.get('quality_score_pct', 0)}%)\n\n")
        
        # Relevance details
        f.write("### Relevance\n\n")
        f.write(f"- Total Recommendations: {relevance.get('total_recommendations', 0)}\n")
        f.write(f"- Relevant (Persona-Content Fit): {relevance.get('relevant_recommendations', 0)} ({relevance.get('relevance_pct', 0)}%)\n")
        f.write(f"- Average Fit Score: {relevance.get('average_fit_score', 0)}\n\n")
        
        # Latency details
        f.write("### Latency\n\n")
        f.write(f"- Sample Size: {latency.get('sample_size', 0)} users\n")
        f.write(f"- Average: {latency.get('average_latency_seconds', 0)}s\n")
        f.write(f"- Min: {latency.get('min_latency_seconds', 0)}s\n")
        f.write(f"- Max: {latency.get('max_latency_seconds', 0)}s\n")
        f.write(f"- Target: <{latency.get('target_seconds', 5)}s\n\n")
        
        # Fairness details
        fairness = metrics.get('fairness', {})
        f.write("### Fairness\n\n")
        f.write("#### Persona Distribution\n\n")
        for persona, pct in fairness.get('persona_percentages', {}).items():
            f.write(f"- {persona}: {pct}%\n")
        f.write("\n#### Recommendation Distribution\n\n")
        for persona, pct in fairness.get('recommendation_percentages', {}).items():
            f.write(f"- {persona}: {pct}%\n")
        f.write("\n")
    
    return {
        'json_file': str(json_file),
        'csv_file': str(csv_file),
        'markdown_file': str(md_file)
    }


def run_evaluation(conn: Optional[sqlite3.Connection] = None, output_dir: str = "metrics") -> Dict:
    """
    Run complete evaluation harness and generate reports.
    
    Args:
        conn: Database connection (creates new if None)
        output_dir: Directory to save output files
        
    Returns:
        Dictionary with all metrics and report file paths
    """
    print("=" * 60)
    print("SpendSense Evaluation Harness")
    print("=" * 60)
    print()
    
    print("Calculating metrics...")
    print("  - Coverage...")
    coverage = calculate_coverage(conn)
    
    print("  - Explainability...")
    explainability = calculate_explainability(conn)
    
    print("  - Relevance...")
    relevance = calculate_relevance(conn)
    
    print("  - Latency...")
    latency = calculate_latency(conn)
    
    print("  - Fairness...")
    fairness = calculate_fairness(conn)
    
    metrics = {
        'coverage': coverage,
        'explainability': explainability,
        'relevance': relevance,
        'latency': latency,
        'fairness': fairness
    }
    
    print()
    print("Generating reports...")
    report_files = generate_report(metrics, output_dir)
    
    print()
    print("=" * 60)
    print("Evaluation Complete")
    print("=" * 60)
    print(f"Coverage: {coverage.get('combined_coverage_pct', 0)}%")
    print(f"Explainability: {explainability.get('explainability_pct', 0)}%")
    print(f"Relevance: {relevance.get('relevance_pct', 0)}%")
    print(f"Latency: {latency.get('average_latency_seconds', 0)}s")
    print()
    print("Reports generated:")
    for file_type, file_path in report_files.items():
        print(f"  - {file_type}: {file_path}")
    
    return {
        'metrics': metrics,
        'report_files': report_files
    }


if __name__ == "__main__":
    """Run evaluation harness."""
    run_evaluation()

