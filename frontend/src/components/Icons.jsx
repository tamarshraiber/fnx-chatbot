const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

export const SendIcon = () => (<svg {...base}><path d="M19 12H5" /><path d="m11 6-6 6 6 6" /></svg>);
export const CopyIcon = () => (<svg {...base}><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V6a2 2 0 0 1 2-2h9" /></svg>);
export const CheckIcon = () => (<svg {...base}><path d="m5 12 5 5 9-10" /></svg>);
export const ExternalIcon = () => (<svg {...base}><path d="M14 4h6v6" /><path d="M20 4 10 14" /><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" /></svg>);
export const ExpandIcon = () => (<svg {...base}><path d="M15 4h5v5" /><path d="M9 20H4v-5" /><path d="m20 4-6 6" /><path d="m4 20 6-6" /></svg>);
export const ShrinkIcon = () => (<svg {...base}><path d="M20 9h-5V4" /><path d="M4 15h5v5" /><path d="m15 9 6-6" /><path d="m9 15-6 6" /></svg>);
export const CloseIcon = () => (<svg {...base}><path d="M6 6l12 12" /><path d="M18 6 6 18" /></svg>);
export const NewChatIcon = () => (<svg {...base}><path d="M12 5v14" /><path d="M5 12h14" /></svg>);
export const ChatIcon = () => (<svg {...base}><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z" /></svg>);
export const RetryIcon = () => (<svg {...base}><path d="M20 11a8 8 0 1 0-2.3 5.7" /><path d="M20 4v7h-7" /></svg>);
