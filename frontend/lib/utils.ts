import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
export const ms = (value: number | null | undefined) =>
  value == null ? "—" : `${value.toFixed(value < 10 ? 2 : 1)} ms`;
export const percent = (value: number | null | undefined) =>
  value == null ? "—" : `${(value * 100).toFixed(0)}%`;
export const shortName = (value: string) => value.replace("user.", "");
