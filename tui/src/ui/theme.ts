export type Theme = {
  borderStyle: "single" | "rounded";
  fg: {
    text: string;
    muted: string;
    good: string;
    warn: string;
    bad: string;
    accent: string;
  };
};

export const theme: Theme = {
  borderStyle: "rounded",
  fg: {
    text: "#E8E8E8",
    muted: "#9AA4B2",
    good: "#4ADE80",
    warn: "#FBBF24",
    bad: "#F87171",
    accent: "#60A5FA",
  },
};
