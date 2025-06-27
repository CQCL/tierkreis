import {
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useShallow } from "zustand/react/shallow";

import useStore from "@/data/store";
import { AppState } from "@/nodes/types";

const selector = (state: AppState) => ({
  info: state.info,
});

export function NodeInfo() {
  const { info } = useStore(useShallow(selector));
  return (
    <DialogContent className="min-w-7xl  sm:max-h-[80vh]">
      <DialogHeader>
        <DialogTitle>{info.type}</DialogTitle>
        <DialogDescription></DialogDescription>
      </DialogHeader>
        <div className="overflow-auto">
      <pre style={{ maxHeight: "65vh" }}>{info.content}</pre>
      </div>
    </DialogContent>
  );
}
