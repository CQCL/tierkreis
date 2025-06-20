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
    <DialogContent className="sm:max-w-7xl overflow-auto">
      <DialogHeader>
        <DialogTitle>{info.type}</DialogTitle>
        <DialogDescription>
          <pre>{info.content}</pre>
        </DialogDescription>
      </DialogHeader>
    </DialogContent>
  );
}
