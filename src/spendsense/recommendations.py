"""
Recommendation engine module for SpendSense MVP.
Generates personalized recommendations based on user personas.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Optional
from .database import get_db_connection
from .personas import get_user_signals
from .rationales import generate_rationale
from .traces import generate_decision_trace
from .eligibility import has_consent
from .tone_validator import validate_and_log
from .content_generator import get_content_generator

# Configure logging
logger = logging.getLogger(__name__)


# Content templates for each persona
TEMPLATES = {
    "high_utilization": [
        {
            "key": "reduce_utilization",
            "title": "Strategies to Lower Your Credit Card Utilization",
            "content": (
                "High credit card utilization can negatively impact your credit score. "
                "Here are strategies to reduce it:\n\n"
                "• Pay more than the minimum payment each month\n"
                "• Consider a balance transfer to a card with lower interest\n"
                "• Create a payment plan to systematically reduce your balance\n"
                "• Avoid new charges on high-utilization cards\n"
                "• Aim to keep utilization below 30% for optimal credit health"
            ),
            "type": "article",
            "always_include": True
        },
        {
            "key": "credit_scores",
            "title": "How Credit Utilization Affects Your Credit Score",
            "content": (
                "Credit utilization is a key factor in your credit score calculation, "
                "accounting for about 30% of your FICO score.\n\n"
                "• Keeping utilization below 30% is ideal\n"
                "• Utilization above 50% can significantly impact your score\n"
                "• Utilization above 80% is considered very high risk\n"
                "• Your score updates as your utilization changes\n"
                "• Even small reductions can help improve your score over time"
            ),
            "type": "article",
            "always_include": True
        },
        {
            "key": "debt_payoff_calculator",
            "title": "Debt Payoff Calculator",
            "content": (
                "Calculate how long it will take to pay off your credit card debt:\n\n"
                "1. Enter your current balance\n"
                "2. Enter your monthly payment amount\n"
                "3. Enter your annual interest rate (APR)\n"
                "4. The calculator shows:\n"
                "   • Total interest you'll pay\n"
                "   • Months to pay off\n"
                "   • How increasing payments affects timeline\n\n"
                "Try paying an extra $50-100/month to see the impact on your payoff date."
            ),
            "type": "calculator",
            "always_include": False
        },
        {
            "key": "payment_plan_template",
            "title": "Debt Payment Plan Template",
            "content": (
                "Create a structured payment plan to reduce your credit card debt:\n\n"
                "Monthly Payment Plan:\n"
                "• Minimum payment: $____\n"
                "• Extra payment: $____\n"
                "• Total monthly payment: $____\n\n"
                "Payment Schedule:\n"
                "• Month 1: $____\n"
                "• Month 2: $____\n"
                "• Month 3: $____\n"
                "• Continue until balance is $0\n\n"
                "Track your progress monthly and adjust as needed."
            ),
            "type": "template",
            "always_include": False
        },
        {
            "key": "credit_review_checklist",
            "title": "Credit Health Review Checklist",
            "content": (
                "Use this checklist to review and improve your credit health:\n\n"
                "□ Check your credit utilization ratio (aim for <30%)\n"
                "□ Review all credit card balances\n"
                "□ Set up payment reminders or autopay\n"
                "□ Check your credit report for errors\n"
                "□ Identify highest interest rate cards\n"
                "□ Create a debt payoff strategy\n"
                "□ Avoid opening new credit accounts\n"
                "□ Monitor your credit score monthly\n"
                "□ Set a target utilization percentage\n"
                "□ Track your progress quarterly"
            ),
            "type": "checklist",
            "always_include": False
        },
        {
            "key": "balance_transfer_guide",
            "title": "Understanding Balance Transfer Cards",
            "content": (
                "Balance transfer cards can help you pay off debt faster by reducing interest charges.\n\n"
                "• Look for cards with 0% APR introductory periods (12-18 months)\n"
                "• Consider balance transfer fees (typically 3-5% of transferred amount)\n"
                "• Calculate if savings outweigh fees\n"
                "• Make sure you can pay off balance before promotional rate ends\n"
                "• Read terms carefully - missed payments may void promotional rate\n"
                "• Continue making payments during promotional period\n"
                "• Avoid using the new card for new purchases"
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "interest_savings_calculator",
            "title": "Interest Savings Calculator",
            "content": (
                "Calculate how much you could save by reducing your credit card interest:\n\n"
                "Current Situation:\n"
                "• Balance: $____\n"
                "• APR: ____%\n"
                "• Monthly payment: $____\n"
                "• Interest paid this year: $____\n\n"
                "With Lower APR (e.g., 0% balance transfer):\n"
                "• New APR: ____%\n"
                "• Interest saved: $____\n"
                "• Months saved: ____\n\n"
                "Use this to decide if a balance transfer makes sense."
            ),
            "type": "calculator",
            "always_include": False
        },
        {
            "key": "autopay",
            "title": "Avoid Missed Payments with Autopay",
            "content": (
                "Setting up autopay ensures you never miss a payment and avoid late fees.\n\n"
                "• Automatically pay your minimum payment each month\n"
                "• Set up to pay more than minimum to reduce balance faster\n"
                "• Choose payment date that aligns with your payday\n"
                "• Monitor your account to ensure payments process correctly\n"
                "• Consider setting up alerts for payment confirmations"
            ),
            "type": "article",
            "always_include": False,
            "condition": "overdue_or_interest"
        },
        {
            "key": "snowball_method",
            "title": "Debt Snowball vs. Debt Avalanche Methods",
            "content": (
                "Two popular debt payoff strategies:\n\n"
                "Debt Snowball Method:\n"
                "• Pay off smallest balance first\n"
                "• Builds momentum with quick wins\n"
                "• Good for motivation\n\n"
                "Debt Avalanche Method:\n"
                "• Pay off highest interest rate first\n"
                "• Saves more money in interest\n"
                "• Better for overall savings\n\n"
                "Choose the method that works best for your personality and financial situation."
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "expense_tracking_template",
            "title": "Monthly Expense Tracking Template",
            "content": (
                "Track expenses to free up money for debt payments:\n\n"
                "Monthly Expenses:\n"
                "• Housing: $____\n"
                "• Food: $____\n"
                "• Transportation: $____\n"
                "• Utilities: $____\n"
                "• Subscriptions: $____\n"
                "• Entertainment: $____\n"
                "• Other: $____\n"
                "• Total: $____\n\n"
                "Identify areas to reduce spending and redirect to debt payments."
            ),
            "type": "template",
            "always_include": False
        },
        {
            "key": "credit_card_optimization",
            "title": "Optimize Your Credit Card Strategy",
            "content": (
                "Make strategic decisions about your credit cards:\n\n"
                "• Prioritize paying off highest APR cards first\n"
                "• Consider consolidating multiple cards if beneficial\n"
                "• Avoid closing old accounts (hurts credit history)\n"
                "• Request lower APR from current card issuers\n"
                "• Use cards with rewards for necessary expenses only\n"
                "• Don't open new cards while paying off debt\n"
                "• Monitor all card balances regularly"
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "debt_free_timeline",
            "title": "Calculate Your Debt-Free Timeline",
            "content": (
                "See when you'll be debt-free with different payment strategies:\n\n"
                "Scenario 1 - Minimum Payments:\n"
                "• Payoff date: ____\n"
                "• Total interest: $____\n\n"
                "Scenario 2 - Extra $50/month:\n"
                "• Payoff date: ____\n"
                "• Total interest: $____\n"
                "• Time saved: ____ months\n\n"
                "Scenario 3 - Extra $100/month:\n"
                "• Payoff date: ____\n"
                "• Total interest: $____\n"
                "• Time saved: ____ months\n\n"
                "Use this to set realistic goals and track progress."
            ),
            "type": "calculator",
            "always_include": False
        },
        {
            "key": "credit_utilization_tracker",
            "title": "Credit Utilization Tracker",
            "content": (
                "Track your credit utilization over time:\n\n"
                "Month 1: ____% (Balance: $____, Limit: $____)\n"
                "Month 2: ____% (Balance: $____, Limit: $____)\n"
                "Month 3: ____% (Balance: $____, Limit: $____)\n"
                "Target: <30%\n\n"
                "Goal: Reduce utilization by ____% each month until below 30%."
            ),
            "type": "template",
            "always_include": False
        }
    ],
    "variable_income_budgeter": [
        {
            "key": "percent_based_budget",
            "title": "Percent-Based Budgeting for Variable Income",
            "content": (
                "When your income varies, use a percent-based budget to maintain financial stability.\n\n"
                "• Allocate 50% to needs (housing, food, utilities)\n"
                "• Allocate 30% to wants (entertainment, dining out)\n"
                "• Allocate 20% to savings and debt payments\n"
                "• Adjust percentages based on your lowest expected income month\n"
                "• Use the highest income months to build your emergency fund"
            ),
            "type": "article",
            "always_include": True
        },
        {
            "key": "emergency_fund",
            "title": "Build Your Emergency Fund",
            "content": (
                "An emergency fund is critical for variable income earners.\n\n"
                "• Aim for 3-6 months of expenses in your emergency fund\n"
                "• Start with a $1,000 mini emergency fund\n"
                "• Save during high-income months to build your fund\n"
                "• Keep emergency fund in a high-yield savings account\n"
                "• Only use it for true emergencies, not income gaps"
            ),
            "type": "article",
            "always_include": True
        },
        {
            "key": "emergency_fund_calculator",
            "title": "Emergency Fund Calculator",
            "content": (
                "Calculate how much you need in your emergency fund:\n\n"
                "1. Calculate monthly expenses: $____\n"
                "2. Multiply by months of coverage needed (3-6 months):\n"
                "   • 3 months: $____\n"
                "   • 6 months: $____\n"
                "3. Current emergency fund: $____\n"
                "4. Amount needed: $____\n"
                "5. Monthly savings goal: $____\n\n"
                "For variable income, aim for 6 months to cover income gaps."
            ),
            "type": "calculator",
            "always_include": False
        },
        {
            "key": "income_smoothing",
            "title": "Income Smoothing Strategies",
            "content": (
                "Smooth out income variability to create more predictable cash flow.\n\n"
                "• Save during high-income months to cover low-income months\n"
                "• Create a monthly 'salary' from your average income\n"
                "• Use a separate account for income smoothing\n"
                "• Track your income patterns to predict future gaps\n"
                "• Consider setting up automatic transfers to savings"
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "variable_income_budget_template",
            "title": "Variable Income Budget Template",
            "content": (
                "Create a budget that adapts to variable income:\n\n"
                "Base Budget (Lowest Expected Income Month):\n"
                "• Needs (50%): $____\n"
                "• Wants (30%): $____\n"
                "• Savings/Debt (20%): $____\n"
                "• Total: $____\n\n"
                "Surplus Allocation (High Income Months):\n"
                "• Emergency fund: $____\n"
                "• Extra debt payment: $____\n"
                "• Short-term goals: $____\n"
                "• Long-term savings: $____\n\n"
                "Track income and adjust allocations monthly."
            ),
            "type": "template",
            "always_include": False
        },
        {
            "key": "income_tracking_checklist",
            "title": "Income Tracking Checklist",
            "content": (
                "Track your variable income effectively:\n\n"
                "□ Record all income sources monthly\n"
                "□ Calculate average monthly income\n"
                "□ Identify highest and lowest income months\n"
                "□ Note seasonal patterns in your income\n"
                "□ Track income gaps (months with no income)\n"
                "□ Set baseline budget from lowest income month\n"
                "□ Plan for income gaps in advance\n"
                "□ Build buffer during high-income months\n"
                "□ Review income patterns quarterly\n"
                "□ Adjust budget based on income trends"
            ),
            "type": "checklist",
            "always_include": False
        },
        {
            "key": "cash_buffer_calculator",
            "title": "Cash Buffer Calculator",
            "content": (
                "Calculate your cash flow buffer for income gaps:\n\n"
                "Monthly Expenses: $____\n"
                "Average Monthly Income: $____\n"
                "Income Gap Months (per year): ____\n\n"
                "Buffer Needed:\n"
                "• For 1-month gap: $____\n"
                "• For 2-month gap: $____\n"
                "• For 3-month gap: $____\n\n"
                "Current Buffer: $____\n"
                "Additional Buffer Needed: $____\n\n"
                "Save this amount during high-income months."
            ),
            "type": "calculator",
            "always_include": False
        },
        {
            "key": "irregular_income_planning",
            "title": "Planning for Irregular Income",
            "content": (
                "Strategies to manage irregular income effectively:\n\n"
                "• Calculate your average monthly income over 6-12 months\n"
                "• Base your budget on your lowest income month\n"
                "• Save all surplus from high-income months\n"
                "• Create separate accounts for different purposes\n"
                "• Build a buffer equal to 2-3 months of expenses\n"
                "• Track income and expenses meticulously\n"
                "• Plan for known income gaps (seasonal work, etc.)\n"
                "• Consider multiple income streams for stability"
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "expense_cutting_guide",
            "title": "Cutting Expenses During Low-Income Months",
            "content": (
                "When income is low, focus on essential expenses:\n\n"
                "Essential Expenses (Keep):\n"
                "• Housing and utilities\n"
                "• Food (basics only)\n"
                "• Transportation (minimum)\n"
                "• Insurance\n\n"
                "Non-Essential Expenses (Cut):\n"
                "• Entertainment\n"
                "• Dining out\n"
                "• Subscriptions\n"
                "• Shopping\n"
                "• Non-essential services\n\n"
                "Track your spending and prioritize needs over wants."
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "income_allocation_template",
            "title": "Income Allocation Template",
            "content": (
                "Allocate income from each pay period:\n\n"
                "Pay Period: ____\n"
                "Income Received: $____\n\n"
                "Allocation:\n"
                "• Needs (50%): $____\n"
                "• Wants (30%): $____\n"
                "• Savings (20%): $____\n\n"
                "Surplus Allocation:\n"
                "• Emergency fund: $____\n"
                "• Income buffer: $____\n"
                "• Debt payment: $____\n\n"
                "Track each pay period separately."
            ),
            "type": "template",
            "always_include": False
        },
        {
            "key": "seasonal_income_planning",
            "title": "Seasonal Income Planning",
            "content": (
                "Plan for seasonal income variations:\n\n"
                "• Identify your high-income and low-income seasons\n"
                "• Save aggressively during peak seasons\n"
                "• Budget conservatively during slow seasons\n"
                "• Build a buffer that covers entire slow season\n"
                "• Consider seasonal work to supplement income\n"
                "• Plan major expenses during high-income periods\n"
                "• Track seasonal patterns over multiple years\n"
                "• Adjust expectations based on historical data"
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "multiple_income_streams",
            "title": "Building Multiple Income Streams",
            "content": (
                "Diversify your income to reduce variability:\n\n"
                "• Maintain primary income source\n"
                "• Add secondary income (part-time, freelance)\n"
                "• Consider passive income opportunities\n"
                "• Build skills that increase earning potential\n"
                "• Network to find additional opportunities\n"
                "• Don't rely on single income source\n"
                "• Balance multiple streams without burnout\n"
                "• Track all income sources separately"
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "variable_expense_tracker",
            "title": "Variable Expense Tracker",
            "content": (
                "Track expenses that vary with income:\n\n"
                "Month: ____\n"
                "Income: $____\n"
                "Expenses:\n"
                "• Fixed: $____\n"
                "• Variable: $____\n"
                "• Total: $____\n\n"
                "Track ratio of expenses to income:\n"
                "• High-income month: ____%\n"
                "• Low-income month: ____%\n"
                "• Average: ____%\n\n"
                "Adjust variable expenses based on income."
            ),
            "type": "template",
            "always_include": False
        }
    ],
    "savings_builder": [
        {
            "key": "goal_setting",
            "title": "Set Clear Savings Goals",
            "content": (
                "You're already building savings! Here's how to optimize your goals:\n\n"
                "• Define specific savings goals (emergency fund, vacation, down payment)\n"
                "• Set target amounts and timelines for each goal\n"
                "• Prioritize your goals based on importance and urgency\n"
                "• Track your progress toward each goal monthly\n"
                "• Celebrate milestones to stay motivated"
            ),
            "type": "article",
            "always_include": True
        },
        {
            "key": "automation",
            "title": "Automate Your Savings",
            "content": (
                "Automation makes saving effortless and consistent.\n\n"
                "• Set up automatic transfers from checking to savings\n"
                "• Use round-up apps to save spare change\n"
                "• Automate savings on your payday\n"
                "• Increase automatic transfers as your income grows\n"
                "• Review and adjust automation quarterly"
            ),
            "type": "article",
            "always_include": True
        },
        {
            "key": "savings_goal_calculator",
            "title": "Savings Goal Calculator",
            "content": (
                "Calculate how long it will take to reach your savings goal:\n\n"
                "Goal: $____\n"
                "Current Savings: $____\n"
                "Monthly Contribution: $____\n"
                "Interest Rate (APY): ____%\n\n"
                "Results:\n"
                "• Months to reach goal: ____\n"
                "• Total interest earned: $____\n"
                "• Total contributions: $____\n\n"
                "Try increasing monthly contribution to reach goal faster."
            ),
            "type": "calculator",
            "always_include": False
        },
        {
            "key": "hysa_education",
            "title": "Maximize Your Savings with High-Yield Accounts",
            "content": (
                "Your savings could earn more with a high-yield savings account.\n\n"
                "• High-yield savings accounts offer 4-5% APY (vs. 0.01% traditional)\n"
                "• Consider certificates of deposit (CDs) for longer-term goals\n"
                "• Compare rates across different financial institutions\n"
                "• Look for accounts with no minimum balance requirements\n"
                "• Keep emergency fund accessible but earning interest"
            ),
            "type": "article",
            "always_include": False,
            "condition": "high_savings"
        },
        {
            "key": "savings_tracker_template",
            "title": "Savings Progress Tracker",
            "content": (
                "Track your savings progress toward multiple goals:\n\n"
                "Goal 1: ____\n"
                "Target: $____ | Current: $____ | Progress: ____%\n\n"
                "Goal 2: ____\n"
                "Target: $____ | Current: $____ | Progress: ____%\n\n"
                "Goal 3: ____\n"
                "Target: $____ | Current: $____ | Progress: ____%\n\n"
                "Update monthly to track progress."
            ),
            "type": "template",
            "always_include": False
        },
        {
            "key": "savings_strategies_checklist",
            "title": "Savings Strategies Checklist",
            "content": (
                "Maximize your savings with these strategies:\n\n"
                "□ Set up automatic transfers to savings\n"
                "□ Use round-up apps for spare change\n"
                "□ Save windfalls (tax refunds, bonuses)\n"
                "□ Increase savings rate with each raise\n"
                "□ Open high-yield savings account\n"
                "□ Create separate accounts for different goals\n"
                "□ Review and cancel unused subscriptions\n"
                "□ Cook at home more to save money\n"
                "□ Use cashback apps and credit rewards\n"
                "□ Track savings progress monthly"
            ),
            "type": "checklist",
            "always_include": False
        },
        {
            "key": "compound_interest_calculator",
            "title": "Compound Interest Calculator",
            "content": (
                "See how compound interest grows your savings:\n\n"
                "Initial Deposit: $____\n"
                "Monthly Contribution: $____\n"
                "Annual Interest Rate: ____%\n"
                "Years: ____\n\n"
                "Results:\n"
                "• Final Balance: $____\n"
                "• Total Contributions: $____\n"
                "• Interest Earned: $____\n\n"
                "The power of compound interest: small regular contributions add up over time."
            ),
            "type": "calculator",
            "always_include": False
        },
        {
            "key": "emergency_fund_guide",
            "title": "Building Your Emergency Fund",
            "content": (
                "An emergency fund is your financial safety net.\n\n"
                "• Aim for 3-6 months of expenses\n"
                "• Start with $1,000 mini emergency fund\n"
                "• Keep in easily accessible high-yield savings account\n"
                "• Only use for true emergencies (not wants)\n"
                "• Replenish after using it\n"
                "• Separate from other savings goals\n"
                "• Review and adjust target amount annually\n"
                "• Automate contributions to build it faster"
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "multiple_goals_template",
            "title": "Multiple Savings Goals Template",
            "content": (
                "Prioritize and track multiple savings goals:\n\n"
                "Priority 1: ____\n"
                "Target: $____ | Timeline: ____ months | Monthly: $____\n\n"
                "Priority 2: ____\n"
                "Target: $____ | Timeline: ____ months | Monthly: $____\n\n"
                "Priority 3: ____\n"
                "Target: $____ | Timeline: ____ months | Monthly: $____\n\n"
                "Total Monthly Savings: $____\n"
                "Adjust priorities and timelines as needed."
            ),
            "type": "template",
            "always_include": False
        },
        {
            "key": "cd_ladder_strategy",
            "title": "CD Ladder Strategy for Savings",
            "content": (
                "Use certificates of deposit (CDs) to maximize returns:\n\n"
                "• Open multiple CDs with staggered maturity dates\n"
                "• Example: 1-year, 2-year, 3-year CDs\n"
                "• Each CD matures at different times\n"
                "• Reinvest maturing CDs or use for goals\n"
                "• Provides both liquidity and higher rates\n"
                "• Compare CD rates across institutions\n"
                "• Consider penalty-free early withdrawal options\n"
                "• Balance access needs with higher rates"
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "savings_rate_calculator",
            "title": "Savings Rate Calculator",
            "content": (
                "Calculate your savings rate:\n\n"
                "Monthly Income: $____\n"
                "Monthly Savings: $____\n"
                "Savings Rate: ____%\n\n"
                "Target Savings Rates:\n"
                "• Beginner: 10-15%\n"
                "• Good: 20-25%\n"
                "• Excellent: 30%+\n\n"
                "Your current rate: ____%\n"
                "Gap to target: ____%\n"
                "Additional monthly savings needed: $____"
            ),
            "type": "calculator",
            "always_include": False
        },
        {
            "key": "sinking_funds",
            "title": "Using Sinking Funds for Planned Expenses",
            "content": (
                "Save for planned expenses with sinking funds:\n\n"
                "• Create separate savings for each planned expense\n"
                "• Examples: vacation, car maintenance, home repairs\n"
                "• Calculate monthly amount needed\n"
                "• Set up automatic transfers\n"
                "• Track progress toward each fund\n"
                "• Prevents using emergency fund for non-emergencies\n"
                "• Reduces financial stress from large expenses\n"
                "• Can combine with high-yield savings accounts"
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "savings_challenge_template",
            "title": "52-Week Savings Challenge Template",
            "content": (
                "Build savings gradually with the 52-week challenge:\n\n"
                "Week 1: Save $1\n"
                "Week 2: Save $2\n"
                "Week 3: Save $3\n"
                "...\n"
                "Week 52: Save $52\n\n"
                "Total Saved: $1,378\n\n"
                "Track your progress:\n"
                "Week: ____ | Amount: $____ | Total: $____\n\n"
                "Adjust amounts to fit your budget."
            ),
            "type": "template",
            "always_include": False
        },
        {
            "key": "retirement_savings_basics",
            "title": "Retirement Savings Basics",
            "content": (
                "Start saving for retirement early:\n\n"
                "• Contribute to employer 401(k) if available\n"
                "• Take advantage of employer matching\n"
                "• Open IRA for additional retirement savings\n"
                "• Aim to save 15-20% of income for retirement\n"
                "• Start small and increase over time\n"
                "• Take advantage of tax benefits\n"
                "• Consider Roth vs. Traditional options\n"
                "• Review and adjust contributions annually"
            ),
            "type": "article",
            "always_include": False
        }
    ],
    "financial_newcomer": [
        {
            "key": "credit_building",
            "title": "Build Your Credit History",
            "content": (
                "Establishing good credit early sets you up for financial success.\n\n"
                "• Consider getting a secured credit card to start building credit\n"
                "• Use credit responsibly by paying balances in full each month\n"
                "• Keep credit utilization below 30%\n"
                "• Make all payments on time to build a positive payment history\n"
                "• Check your credit report regularly (free annually from each bureau)"
            ),
            "type": "article",
            "always_include": True
        },
        {
            "key": "account_basics",
            "title": "Understanding Your Financial Accounts",
            "content": (
                "Learn the basics of managing your financial accounts effectively.\n\n"
                "• Understand the difference between checking and savings accounts\n"
                "• Set up online banking to monitor your accounts regularly\n"
                "• Enable account alerts for transactions and balances\n"
                "• Reconcile your accounts monthly to catch errors early\n"
                "• Keep your account information secure and private"
            ),
            "type": "article",
            "always_include": True
        },
        {
            "key": "simple_budget_template",
            "title": "Simple Budget Template for Beginners",
            "content": (
                "Create your first budget with this simple template:\n\n"
                "Monthly Income: $____\n\n"
                "Expenses:\n"
                "• Housing: $____\n"
                "• Food: $____\n"
                "• Transportation: $____\n"
                "• Utilities: $____\n"
                "• Other: $____\n"
                "• Total Expenses: $____\n\n"
                "Income - Expenses: $____\n"
                "Allocate remainder to savings or debt."
            ),
            "type": "template",
            "always_include": False
        },
        {
            "key": "financial_foundations",
            "title": "Establish Good Financial Habits Early",
            "content": (
                "Good habits formed early will serve you throughout your financial life.\n\n"
                "• Create a simple budget to track income and expenses\n"
                "• Start building an emergency fund, even if it's small\n"
                "• Set clear financial goals for the short and long term\n"
                "• Educate yourself about personal finance basics\n"
                "• Avoid taking on debt you can't afford to repay"
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "first_budget_checklist",
            "title": "First Budget Checklist",
            "content": (
                "Steps to create your first budget:\n\n"
                "□ List all sources of monthly income\n"
                "□ Track all expenses for one month\n"
                "□ Categorize expenses (needs vs. wants)\n"
                "□ Compare income to expenses\n"
                "□ Identify areas to reduce spending\n"
                "□ Set savings goals\n"
                "□ Create spending plan for next month\n"
                "□ Review and adjust budget monthly\n"
                "□ Use budgeting app or spreadsheet\n"
                "□ Celebrate sticking to your budget"
            ),
            "type": "checklist",
            "always_include": False
        },
        {
            "key": "emergency_fund_calculator_basic",
            "title": "Emergency Fund Calculator (Beginner)",
            "content": (
                "Calculate your first emergency fund goal:\n\n"
                "Monthly Expenses: $____\n"
                "Mini Emergency Fund (Target): $1,000\n"
                "Current Savings: $____\n"
                "Amount Needed: $____\n\n"
                "Monthly Savings Goal:\n"
                "• To reach $1,000 in 6 months: $____/month\n"
                "• To reach $1,000 in 12 months: $____/month\n\n"
                "Start small and build gradually."
            ),
            "type": "calculator",
            "always_include": False
        },
        {
            "key": "banking_basics",
            "title": "Banking Basics for Beginners",
            "content": (
                "Essential banking knowledge:\n\n"
                "• Checking account: for daily transactions\n"
                "• Savings account: for short-term goals\n"
                "• Online banking: convenient access 24/7\n"
                "• Mobile banking: manage money on the go\n"
                "• Direct deposit: automatic paycheck deposits\n"
                "• Overdraft protection: avoid fees\n"
                "• Account alerts: stay informed\n"
                "• FDIC insurance: protects your deposits"
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "expense_tracking_template_simple",
            "title": "Simple Expense Tracker",
            "content": (
                "Track expenses for one week:\n\n"
                "Day 1: $____ (Category: ____)\n"
                "Day 2: $____ (Category: ____)\n"
                "Day 3: $____ (Category: ____)\n"
                "Day 4: $____ (Category: ____)\n"
                "Day 5: $____ (Category: ____)\n"
                "Day 6: $____ (Category: ____)\n"
                "Day 7: $____ (Category: ____)\n\n"
                "Weekly Total: $____\n"
                "Track patterns and identify spending habits."
            ),
            "type": "template",
            "always_include": False
        },
        {
            "key": "debt_avoidance",
            "title": "Avoiding Debt as a Financial Newcomer",
            "content": (
                "Build good habits to avoid debt:\n\n"
                "• Live within your means\n"
                "• Save before spending on wants\n"
                "• Use credit cards responsibly (pay in full)\n"
                "• Avoid payday loans and high-interest debt\n"
                "• Build emergency fund before taking on debt\n"
                "• Understand interest rates before borrowing\n"
                "• Only borrow for appreciating assets (education, home)\n"
                "• Create budget to prevent overspending"
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "financial_goals_template",
            "title": "Financial Goals Template",
            "content": (
                "Set your first financial goals:\n\n"
                "Short-term Goals (0-1 year):\n"
                "• Goal 1: ____ | Target: $____ | Deadline: ____\n"
                "• Goal 2: ____ | Target: $____ | Deadline: ____\n\n"
                "Medium-term Goals (1-5 years):\n"
                "• Goal 1: ____ | Target: $____ | Deadline: ____\n\n"
                "Long-term Goals (5+ years):\n"
                "• Goal 1: ____ | Target: $____ | Deadline: ____\n\n"
                "Review and update goals quarterly."
            ),
            "type": "template",
            "always_include": False
        },
        {
            "key": "credit_score_basics",
            "title": "Understanding Your Credit Score",
            "content": (
                "Learn the basics of credit scores:\n\n"
                "• Credit scores range from 300-850\n"
                "• Factors: payment history, utilization, age, mix, inquiries\n"
                "• Payment history is most important (35%)\n"
                "• Utilization should be below 30% (30%)\n"
                "• Check your score regularly (free options available)\n"
                "• Build credit with responsible credit card use\n"
                "• Avoid late payments at all costs\n"
                "• Time is your friend - credit history improves with age"
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "financial_health_checklist",
            "title": "Financial Health Checklist",
            "content": (
                "Assess your financial health:\n\n"
                "□ Have a budget\n"
                "□ Track expenses regularly\n"
                "□ Have emergency fund ($1,000+)\n"
                "□ Have checking and savings accounts\n"
                "□ Pay bills on time\n"
                "□ Have financial goals\n"
                "□ Understand credit score\n"
                "□ Use credit responsibly\n"
                "□ Save money each month\n"
                "□ Review finances monthly"
            ),
            "type": "checklist",
            "always_include": False
        }
    ],
    "subscription_heavy": [
        {
            "key": "audit_subscriptions",
            "title": "Review Your Recurring Subscriptions",
            "content": (
                "You have multiple recurring subscriptions. Here's a checklist to review them:\n\n"
                "• List all your active subscriptions\n"
                "• Identify services you no longer use\n"
                "• Calculate your total monthly subscription cost\n"
                "• Prioritize which subscriptions provide the most value\n"
                "• Consider canceling unused services to save money"
            ),
            "type": "article",
            "always_include": True
        },
        {
            "key": "subscription_audit_checklist",
            "title": "Subscription Audit Checklist",
            "content": (
                "Complete subscription audit:\n\n"
                "□ List all active subscriptions\n"
                "□ Note monthly cost for each\n"
                "□ Calculate total monthly spend\n"
                "□ Identify last used date for each\n"
                "□ Mark subscriptions you use regularly\n"
                "□ Mark subscriptions you rarely use\n"
                "□ Check for duplicate services\n"
                "□ Look for bundle opportunities\n"
                "□ Cancel unused subscriptions\n"
                "□ Review quarterly"
            ),
            "type": "checklist",
            "always_include": False
        },
        {
            "key": "subscription_tracker_template",
            "title": "Subscription Tracker Template",
            "content": (
                "Track all your subscriptions:\n\n"
                "Service: ____ | Cost: $____/month | Used: Yes/No | Cancel: Yes/No\n"
                "Service: ____ | Cost: $____/month | Used: Yes/No | Cancel: Yes/No\n"
                "Service: ____ | Cost: $____/month | Used: Yes/No | Cancel: Yes/No\n"
                "Service: ____ | Cost: $____/month | Used: Yes/No | Cancel: Yes/No\n\n"
                "Total Monthly Cost: $____\n"
                "Annual Cost: $____\n"
                "Update monthly."
            ),
            "type": "template",
            "always_include": False
        },
        {
            "key": "negotiation",
            "title": "How to Reduce Subscription Costs",
            "content": (
                "Many subscription services offer discounts or can be negotiated. Here's how:\n\n"
                "• Contact customer service to ask about promotional rates\n"
                "• Switch to annual plans for better per-month pricing\n"
                "• Look for student, family, or bundle discounts\n"
                "• Consider sharing family plans with trusted friends/family\n"
                "• Review your usage and downgrade to lower tiers if needed"
            ),
            "type": "article",
            "always_include": False,
            "condition": "high_spend"
        },
        {
            "key": "subscription_savings_calculator",
            "title": "Subscription Savings Calculator",
            "content": (
                "Calculate potential savings from canceling subscriptions:\n\n"
                "Current Monthly Subscriptions: $____\n"
                "Subscriptions to Cancel: $____\n"
                "New Monthly Total: $____\n\n"
                "Savings:\n"
                "• Monthly: $____\n"
                "• Annual: $____\n\n"
                "What you could do with savings:\n"
                "• Emergency fund contribution: $____/year\n"
                "• Debt payment: $____/year\n"
                "• Investment: $____/year"
            ),
            "type": "calculator",
            "always_include": False
        },
        {
            "key": "bill_alerts",
            "title": "Track Your Recurring Charges",
            "content": (
                "Set up alerts to track when subscriptions renew and how much they cost.\n\n"
                "• Enable email notifications for recurring charges\n"
                "• Set calendar reminders before renewal dates\n"
                "• Review your bank statements monthly for subscription charges\n"
                "• Use budgeting apps to track subscription spending\n"
                "• Regularly audit your subscriptions (quarterly or annually)"
            ),
            "type": "article",
            "always_include": True
        },
        {
            "key": "subscription_rotation",
            "title": "Subscription Rotation Strategy",
            "content": (
                "Rotate subscriptions to save money:\n\n"
                "• Subscribe to one streaming service at a time\n"
                "• Watch what you want, then cancel and switch\n"
                "• Rotate based on new content releases\n"
                "• Share accounts with family (where allowed)\n"
                "• Use free trials before committing\n"
                "• Take advantage of promotional periods\n"
                "• Cancel before renewal dates\n"
                "• Track what you actually use"
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "free_alternatives",
            "title": "Free Alternatives to Paid Subscriptions",
            "content": (
                "Consider free alternatives before paying:\n\n"
                "• Library apps for books and movies\n"
                "• Free streaming services (with ads)\n"
                "• Free versions of productivity apps\n"
                "• Open-source software alternatives\n"
                "• Free trials before committing\n"
                "• Student discounts where available\n"
                "• Family sharing plans\n"
                "• Evaluate if free version meets needs"
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "subscription_negotiation_template",
            "title": "Subscription Negotiation Template",
            "content": (
                "Track subscription negotiations:\n\n"
                "Service: ____\n"
                "Current Price: $____/month\n"
                "Negotiation Date: ____\n"
                "Strategy Used: ____\n"
                "Result: ____\n"
                "New Price: $____/month\n"
                "Savings: $____/year\n\n"
                "Document what worked for future reference."
            ),
            "type": "template",
            "always_include": False
        },
        {
            "key": "subscription_value_analysis",
            "title": "Subscription Value Analysis",
            "content": (
                "Evaluate value of each subscription:\n\n"
                "For each subscription, calculate:\n"
                "• Cost per use: $____/use\n"
                "• Hours of entertainment: ____ hours/month\n"
                "• Value rating (1-10): ____\n"
                "• Can live without it: Yes/No\n\n"
                "Cancel subscriptions with:\n"
                "• High cost per use\n"
                "• Low value rating\n"
                "• Low usage\n"
                "• Easy to replace"
            ),
            "type": "article",
            "always_include": False
        },
        {
            "key": "subscription_cleanup_checklist",
            "title": "Subscription Cleanup Checklist",
            "content": (
                "Steps to clean up subscriptions:\n\n"
                "□ Review all bank statements for subscriptions\n"
                "□ List every recurring charge\n"
                "□ Identify subscriptions you forgot about\n"
                "□ Check for free trials that converted\n"
                "□ Cancel unused subscriptions\n"
                "□ Negotiate better rates\n"
                "□ Switch to annual plans where cheaper\n"
                "□ Set reminders before renewals\n"
                "□ Track subscription spending monthly\n"
                "□ Review quarterly"
            ),
            "type": "checklist",
            "always_include": False
        }
    ],
    "neutral": [
        {
            "key": "financial_habits",
            "title": "Build Healthy Financial Habits",
            "content": (
                "Establishing good financial habits can help you achieve your goals.\n\n"
                "• Create a monthly budget and track your spending\n"
                "• Build an emergency fund with 3-6 months of expenses\n"
                "• Set up automatic savings transfers\n"
                "• Review your financial goals regularly\n"
                "• Educate yourself about personal finance topics"
            ),
            "always_include": True
        },
        {
            "key": "savings_tips",
            "title": "Simple Ways to Save Money",
            "content": (
                "Small changes can add up to significant savings over time.\n\n"
                "• Review your recurring expenses monthly\n"
                "• Cook at home more often\n"
                "• Use cashback apps and credit card rewards\n"
                "• Compare prices before major purchases\n"
                "• Set specific savings goals to stay motivated"
            ),
            "always_include": True
        },
        {
            "key": "credit_education",
            "title": "Understanding Credit and Debt",
            "content": (
                "A solid understanding of credit can help you make better financial decisions.\n\n"
                "• Learn how credit scores are calculated\n"
                "• Understand the difference between good and bad debt\n"
                "• Know your credit utilization ratio\n"
                "• Check your credit report regularly\n"
                "• Use credit responsibly to build a strong credit history"
            ),
            "always_include": True
        }
    ]
}


def get_templates_for_persona(persona_type: str) -> List[Dict]:
    """
    Get content templates for a persona.
    
    Args:
        persona_type: Persona type (high_utilization, subscription_heavy, neutral)
        
    Returns:
        List of template dictionaries
    """
    return TEMPLATES.get(persona_type, TEMPLATES["neutral"])


def select_template(key: str, templates: List[Dict]) -> Optional[Dict]:
    """
    Select a specific template by key.
    
    Args:
        key: Template key
        templates: List of template dictionaries
        
    Returns:
        Template dictionary or None if not found
    """
    for template in templates:
        if template.get("key") == key:
            return template
    return None


def get_user_persona(user_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[str]:
    """
    Get assigned persona for a user.
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        
    Returns:
        Persona type or None if not assigned
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT persona_type FROM personas WHERE user_id = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        if close_conn:
            conn.close()


def store_recommendation(user_id: int, title: str, content: str, rationale: str,
                        persona_matched: str, conn: Optional[sqlite3.Connection] = None) -> int:
    """
    Store recommendation in database.
    
    Args:
        user_id: User ID
        title: Recommendation title
        content: Recommendation content
        rationale: Data-driven rationale
        persona_matched: Persona type
        conn: Database connection (creates new if None)
        
    Returns:
        Recommendation ID
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO recommendations (
                user_id, title, content, rationale, persona_matched
            ) VALUES (?, ?, ?, ?, ?)
        """, (user_id, title, content, rationale, persona_matched))
        
        recommendation_id = cursor.lastrowid
        conn.commit()
        
        return recommendation_id
    finally:
        if close_conn:
            conn.close()


def generate_recommendations(user_id: int, conn: Optional[sqlite3.Connection] = None) -> List[int]:
    """
    Generate 2-3 personalized recommendations for a user.
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        
    Returns:
        List of recommendation IDs (empty if consent not given)
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        # Check consent first - block recommendations without consent
        if not has_consent(user_id, conn):
            return []  # No recommendations without consent
        
        # Get user persona
        persona = get_user_persona(user_id, conn)
        if not persona:
            # If no persona assigned, assign one
            from personas import assign_persona
            persona = assign_persona(user_id, conn)
        
        # Get user signals for rationale generation
        signals_list = get_user_signals(user_id, conn)
        # Convert to dict for easier lookup
        signals_dict = {}
        for signal in signals_list:
            signals_dict[signal['signal_type']] = signal
        
        # Get user accounts for context
        cursor = conn.cursor()
        cursor.execute("""
            SELECT type, subtype, current_balance, "limit"
            FROM accounts WHERE user_id = ?
        """, (user_id,))
        accounts = []
        for row in cursor.fetchall():
            accounts.append({
                'type': row[0],
                'subtype': row[1],
                'current_balance': row[2] or 0,
                'limit': row[3] or 0
            })
        
        # Try OpenAI generation first (if available)
        ai_recommendations = None
        try:
            content_generator = get_content_generator()
            user_context = {
                'persona': persona,
                'signals': signals_dict,
                'accounts': accounts
            }
            ai_result = content_generator.generate_recommendation(user_context)
            if ai_result and ai_result.get('recommendations'):
                ai_recommendations = ai_result['recommendations']
                logger.info(f"Generated {len(ai_recommendations)} AI recommendations for user {user_id}")
        except Exception as e:
            logger.warning(f"OpenAI generation failed for user {user_id}: {e}, falling back to templates")
            ai_recommendations = None
        
        # Use AI recommendations if available and valid, otherwise use templates
        if ai_recommendations:
            # Validate AI-generated content and use if valid
            valid_ai_recs = []
            for ai_rec in ai_recommendations[:5]:  # Limit to 5 AI recommendations
                title = ai_rec.get('title', '')
                content = ai_rec.get('content', '')
                
                # Validate tone
                content_valid = validate_and_log(user_id, content, "ai_recommendation_content")
                if content_valid:
                    # Add disclaimer if not present
                    if "This is educational content, not financial advice" not in content:
                        content += "\n\nThis is educational content, not financial advice."
                    
                    valid_ai_recs.append({
                        'title': title,
                        'content': content,
                        'type': ai_rec.get('type', 'article'),
                        'key': f"ai_{len(valid_ai_recs)}",
                        'source': 'openai'
                    })
                else:
                    logger.warning(f"AI-generated content failed tone validation for user {user_id}, skipping")
            
            if valid_ai_recs:
                recommendations = valid_ai_recs[:3]  # Limit to 3 AI recommendations
            else:
                # All AI recommendations failed validation, fallback to templates
                logger.info(f"All AI recommendations failed validation for user {user_id}, using templates")
                recommendations = []
        else:
            # No AI recommendations, use templates
            recommendations = []
        
        # Fallback to templates if no AI recommendations
        if not recommendations:
            # Get templates for persona
            templates = get_templates_for_persona(persona)
            
            # Select recommendations
            used_titles = set()
            
            # Always include templates marked as always_include
            for template in templates:
                if template.get("always_include", False):
                    key = template.get("key")
                    if key not in used_titles:
                        recommendations.append(template)
                        used_titles.add(key)
            
            # Check conditional templates
            for template in templates:
                if template.get("key") in used_titles:
                    continue
                
                condition = template.get("condition")
                if condition == "overdue_or_interest":
                    overdue = signals_dict.get('credit_overdue', {}).get('value', 0) or 0
                    interest = signals_dict.get('credit_interest_charges', {}).get('value', 0) or 0
                    if overdue == 1.0 or interest > 0:
                        recommendations.append(template)
                        used_titles.add(template.get("key"))
                elif condition == "high_spend":
                    monthly_spend = signals_dict.get('subscription_monthly_spend', {}).get('value', 0) or 0
                    if monthly_spend >= 75.0:
                        recommendations.append(template)
                        used_titles.add(template.get("key"))
            
            # Ensure we have at least 2 recommendations
            if len(recommendations) < 2:
                # Add more templates if needed
                for template in templates:
                    if template.get("key") not in used_titles:
                        recommendations.append(template)
                        used_titles.add(template.get("key"))
                        if len(recommendations) >= 3:
                            break
            
            # Limit to 2-3 recommendations
            recommendations = recommendations[:3]
        
        # Generate and store recommendations
        recommendation_ids = []
        
        for template in recommendations:
            # Validate content tone
            content_valid = validate_and_log(user_id, template['content'], "recommendation_content")
            
            # Generate rationale
            rationale = generate_rationale(user_id, {
                'title': template['title'],
                'persona_matched': persona
            }, signals_dict, conn)
            
            # Validate rationale tone
            rationale_valid = validate_and_log(user_id, rationale, "rationale")
            
            # Store recommendation (even if tone violations found - we log but don't block)
            # In production, might want to flag for manual review
            rec_id = store_recommendation(
                user_id,
                template['title'],
                template['content'],
                rationale,
                persona,
                conn
            )
            
            recommendation_ids.append(rec_id)
            
            # Generate decision trace
            generate_decision_trace(
                user_id,
                rec_id,
                persona,
                template,
                signals_dict,
                conn
            )
        
        return recommendation_ids
        
    finally:
        if close_conn:
            conn.close()


def generate_recommendations_for_all_users(conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Generate recommendations for all users in the database.
    
    Args:
        conn: Database connection (creates new if None)
        
    Returns:
        Summary dictionary with results
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users")
        user_ids = [row[0] for row in cursor.fetchall()]
        
        summary = {
            'users_processed': 0,
            'total_recommendations': 0,
            'results': []
        }
        
        for user_id in user_ids:
            print(f"Generating recommendations for user {user_id}...")
            rec_ids = generate_recommendations(user_id, conn)
            summary['users_processed'] += 1
            summary['total_recommendations'] += len(rec_ids)
            summary['results'].append({
                'user_id': user_id,
                'recommendation_count': len(rec_ids),
                'recommendation_ids': rec_ids
            })
            print(f"  ✓ Generated {len(rec_ids)} recommendations")
        
        return summary
        
    finally:
        if close_conn:
            conn.close()


if __name__ == "__main__":
    """Run recommendation generation for all users."""
    print("=" * 60)
    print("SpendSense - Recommendation Generation")
    print("=" * 60)
    print()
    
    summary = generate_recommendations_for_all_users()
    
    print()
    print("=" * 60)
    print("Generation Summary:")
    print(f"  Users processed: {summary['users_processed']}")
    print(f"  Total recommendations: {summary['total_recommendations']}")
    print("=" * 60)

