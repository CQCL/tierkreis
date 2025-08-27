import clsx from "clsx";
import { ReactNode } from "react";

export type NodeStatusIndicatorProps = {
  status?: "Not started" | "Started" | "Error" | "Finished";
  children: ReactNode;
};

export const LoadingIndicator = ({ children }: { children: ReactNode }) => {
  return (
    <>
      <div
        className="absolute -left-[1px] -top-[1px] h-[calc(100%+2px)] w-[calc(100%+2px)]"
        style={{ zIndex: "-1" }}
      >
        <style>
          {`
        @keyframes spin {
          from { transform: translate(-50%, -50%) rotate(0deg); }
          to { transform: translate(-50%, -50%) rotate(360deg); }
        }
        .spinner {
          animation: spin 2s linear infinite;
          position: absolute;
          left: 50%;
          top: 50%;
          width: 140%;
          aspect-ratio: 1;
          transform-origin: center;
          z-index: -1; // manual fix for the card
          }
      `}
        </style>
        <div
          className="absolute inset-0 overflow-hidden rounded-xl"
          style={{ zIndex: "-1" }}
        >
          <div className="spinner rounded-full bg-[conic-gradient(from_0deg_at_50%_50%,_rgb(42,67,233)_0deg,_rgba(42,138,246,0)_360deg)]" />
        </div>
      </div>
      {children}
    </>
  );
};

const StatusBorder = ({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) => {
  return (
    <>
      <div
        className={clsx(
          "absolute -left-[1px] -top-[1px] h-[calc(100%+2px)] w-[calc(100%+2px)] rounded-xl border-2",
          className
        )}
        style={{ pointerEvents: "none" }}
      />
      {children}
    </>
  );
};

export const NodeStatusIndicator = ({
  status,
  children,
}: NodeStatusIndicatorProps) => {
  switch (status) {
    case "Started":
      return <StatusBorder className="border-chart-4">{children}</StatusBorder>;
    case "Finished":
      return (
        <StatusBorder className="border-emerald-600">{children}</StatusBorder>
      );
    case "Error":
      return <StatusBorder className="border-red-400">{children}</StatusBorder>;
    default:
      return <>{children}</>;
  }
};
