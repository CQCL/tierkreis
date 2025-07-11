import {
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { InfoProps } from "./types";

export function NodeInfo(props: { info: InfoProps }) {
  return (
    <DialogContent className="min-w-7xl  sm:max-h-[80vh]">
      <DialogHeader>
        <DialogTitle>{props.info.type}</DialogTitle>
        <DialogDescription></DialogDescription>
      </DialogHeader>
      <div className="overflow-auto">
        <pre style={{ maxHeight: "65vh" }}>{props.info.content}</pre>
      </div>
    </DialogContent>
  );
}
