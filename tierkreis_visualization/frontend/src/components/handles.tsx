import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Handle, Position } from "@xyflow/react";

interface Props {
  handles: string[];
  id: string;
}
// I have no idea about the style, but it seems to be working now
export const InputHandleArray = ({ handles, id }: Props) => {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-around",
        alignItems: "center",
        position: "absolute",
        gap: 1,
        top: 0,
        left: 0,
        width: "100%",
      }}
    >
      {[... new Set(handles)].map((key) => {
        return (
          <div
            key={key}
            style={{
              display: "flex",
              alignItems: "center",
              justifySelf: "center",
              gap: 0.5,
            }}
          >
            <>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Handle
                    type="target"
                    id={id + "_" + key.toString()}
                    position={Position.Top}
                    style={{
                      position: "initial",
                      //transform: "initial",
                      height: "0.875rem",
                      width: "0.875rem",
                      border: "none",
                      // background: theme.palette.text.disabled,
                    }}
                  />
                </TooltipTrigger>
                <TooltipContent>
                  <p>{id + "_" + key.toString()}</p>
                </TooltipContent>
              </Tooltip>
            </>
          </div>
        );
      })}
    </div>
  );
};

export const OutputHandleArray = ({ handles, id }: Props) => {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-around",
        alignItems: "center",
        position: "absolute",
        gap: 1,
        bottom: 0,
        left: 0,
        width: "100%",
      }}
    >
      {[... new Set(handles)].map((key) => {
        return (
          <div
            key={key}
            style={{
              display: "flex",
              alignItems: "center",
              justifySelf: "center",
              gap: 0.5,
            }}
          >
            <>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Handle
                    type="source"
                    id={id + "_" + key.toString()}
                    position={Position.Bottom}
                    style={{
                      position: "initial",
                      //transform: "initial",
                      height: "0.875rem",
                      width: "0.875rem",
                      border: "none",
                      // background: theme.palette.text.disabled,
                    }}
                  />
                </TooltipTrigger>
                <TooltipContent>
                  <p>{id + "_" + key.toString()}</p>
                </TooltipContent>
              </Tooltip>
            </>
          </div>
        );
      })}
    </div>
  );
};
