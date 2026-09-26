import type { SVGProps } from "react";

type P = SVGProps<SVGSVGElement> & { size?: number };
const base = (size = 20): SVGProps<SVGSVGElement> => ({
  width: size, height: size, viewBox: "0 0 24 24", fill: "none",
  stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round",
});

export const SearchIcon = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>);
export const CartIcon = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><circle cx="9" cy="20" r="1.3" /><circle cx="18" cy="20" r="1.3" /><path d="M2.5 3h2.7l2.4 11.2a1.5 1.5 0 0 0 1.5 1.2h8.6a1.5 1.5 0 0 0 1.5-1.1L21 7H6" /></svg>);
export const UserIcon = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><circle cx="12" cy="8" r="4" /><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" /></svg>);
export const ShareIcon = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><circle cx="18" cy="5" r="2.6" /><circle cx="6" cy="12" r="2.6" /><circle cx="18" cy="19" r="2.6" /><path d="m8.4 13.4 7.2 4.2M15.6 6.4l-7.2 4.2" /></svg>);
export const ChevronDown = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="m6 9 6 6 6-6" /></svg>);
export const ChevronLeft = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="m15 6-6 6 6 6" /></svg>);
export const ChevronRight = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="m9 6 6 6-6 6" /></svg>);
export const PlusCircle = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><circle cx="12" cy="12" r="9" /><path d="M12 8v8M8 12h8" /></svg>);
export const StarIcon = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z" /></svg>);
export const LangIcon = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><rect x="3" y="3" width="11" height="11" rx="2" /><path d="M6 7h5M8.5 7v4M13 13l3.5-8 3.5 8M14 11h5" /><path d="M10 17c0 2 1.5 4 4 4" /></svg>);
export const CloseIcon = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M6 6l12 12M18 6 6 18" /></svg>);
export const SparkIcon = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6" /></svg>);
export const SendIcon = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M20 4 3 11l7 2 2 7z" /><path d="m10 13 4-4" /></svg>);
export const TrashIcon = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13" /></svg>);
export const CheckIcon = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="m5 12 5 5 9-10" /></svg>);
export const ChatIcon = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M4 5h16v11H9l-5 4z" /><path d="M8 10h8M8 13h5" /></svg>);
export const BellIcon = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M6 16V11a6 6 0 1 1 12 0v5l2 2H4z" /><path d="M10 21h4" /></svg>);
export const FlaskIcon = ({ size, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M9 3h6M10 3v6L4.5 19a1.5 1.5 0 0 0 1.3 2h12.4a1.5 1.5 0 0 0 1.3-2L14 9V3" /><path d="M7 15h10" /></svg>);
