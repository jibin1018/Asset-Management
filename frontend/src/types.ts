export type Kind = 'expense' | 'income' | 'transfer';

export interface AccountType {
  label: string;
  group: string;
  liability?: boolean;
}

export interface Category {
  name: string;
  kind: Kind;
  bucket?: 'need' | 'want';
}

export interface Meta {
  account_types: Record<string, AccountType>;
  groups: Record<string, { label: string; color: string }>;
  categories: Category[];
}

export interface Account {
  id: number;
  name: string;
  type: string;
  institution: string;
  balance: number;
  principal: number | null;
  interest_rate: number | null;
  expire_date: string | null;
  monthly_payment: number | null;
  note: string;
  updated_at: string;
}

export interface Transaction {
  id: number;
  date: string;
  account_id: number;
  amount: number;
  direction: 1 | -1;
  description: string;
  category: string;
  kind: Kind;
  manual_category: boolean;
  source: string;
}

export interface TransactionList {
  items: Transaction[];
  total: number;
  income: number;
  expense: number;
  transfer: number;
}

export interface MonthSummary {
  month: string;
  income: number;
  expense: number;
  net: number;
  transfer: number;
  count: number;
  by_category: Record<string, number>;
}

export type Level = 'danger' | 'warn' | 'info' | 'good';

export interface Advice {
  level: Level;
  title: string;
  body: string;
  saving: number | null;
}

export interface Dashboard {
  month: string;
  net_worth: { assets: number; debts: number; net: number; by_group: Record<string, number> };
  groups: { key: string; label: string; color: string; value: number }[];
  summary: MonthSummary;
  prev_summary: MonthSummary;
  savings_rate: number | null;
  target_rate: number;
  monthly: { month: string; income: number; expense: number }[];
  snapshots: { date: string; net: number }[];
  advice: Advice[];
}

export interface GoalStatus {
  id: number;
  name: string;
  target: number;
  current: number;
  deadline: string | null;
  account_id: number | null;
  effective_current: number;
  progress: number;
  months_left: number | null;
  monthly_needed: number | null;
}

export interface Plan {
  based_on_months: number;
  income: number;
  expense: number;
  surplus: number;
  target_rate: number;
  target: number;
  cuts: { category: string; current: number; cut: number; suggested: number }[];
  monthly_saving: number;
  emergency: { cash: number; target: number; gap: number };
  allocation: { name: string; amount: number; note: string }[];
  goals: GoalStatus[];
}

export interface Subscription {
  name: string;
  category: string;
  monthly: number;
  annual: number;
  months: number;
  last_date: string;
  essential: boolean;
}

export interface Insights {
  month: string;
  advice: Advice[];
  plan: Plan;
  subscriptions: Subscription[];
  trend: { months: string[]; rows: { category: string; values: number[] }[] };
  averages: { months: number; income: number; expense: number; by_category: Record<string, number> };
}

export interface BudgetRow {
  category: string;
  bucket: 'need' | 'want' | null;
  limit: number | null;
  spent: number;
  average: number;
}

export interface ImportMapping {
  date: number | null;
  description: number | null;
  memo: number | null;
  amount: number | null;
  withdraw: number | null;
  deposit: number | null;
}

export type ImportMode = 'split' | 'single';
export type ImportSign = 'negative_expense' | 'positive_expense';

export interface ParsedFile {
  file_name: string;
  rows: string[][];
  header_index: number;
  mapping: ImportMapping;
  mode: ImportMode;
  sign: ImportSign;
}

export interface ImportResult {
  total: number;
  added: number;
  duplicates: number;
  skipped: number;
  preview: {
    date: string;
    amount: number;
    direction: number;
    description: string;
    category: string;
    kind: Kind;
    duplicate: boolean;
  }[];
}

export interface Settings {
  savings_target_rate: number;
  emergency_months: number;
  monthly_income: number;
}

export interface Rule {
  id: number;
  keyword: string;
  category: string;
}
