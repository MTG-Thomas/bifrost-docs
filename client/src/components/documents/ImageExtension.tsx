import Image from "@tiptap/extension-image";
import { ReactNodeViewRenderer } from "@tiptap/react";
import { ImageWithSkeleton } from "./ImageWithSkeleton";

export const ImageExtension = Image.extend({
  addNodeView() {
    return ReactNodeViewRenderer(ImageWithSkeleton);
  },
});
