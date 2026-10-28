/* Adapted from Vercel AI Elements conversation.tsx and message.tsx.
 * Copyright 2023 Vercel, Inc. Apache-2.0; see THIRD_PARTY_NOTICES.md.
 * Changes: project CSS, native buttons, reduced motion, no AI SDK dependency.
 */
import { useEffect, useState, type ComponentProps } from "react";
import { ArrowDown } from "lucide-react";
import { StickToBottom, useStickToBottomContext } from "use-stick-to-bottom";

export function Conversation(props: ComponentProps<typeof StickToBottom>) {
  const [reducedMotion, setReducedMotion] = useState(
    () => matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  useEffect(() => {
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return (
    <StickToBottom
      role="log"
      initial="instant"
      resize={reducedMotion ? "instant" : "smooth"}
      {...props}
    />
  );
}

export const ConversationContent = StickToBottom.Content;

export function ConversationScrollButton() {
  const { isAtBottom, scrollToBottom } = useStickToBottomContext();
  return !isAtBottom ? (
    <button
      type="button"
      className="scroll-latest"
      onClick={() =>
        void scrollToBottom({
          animation: matchMedia("(prefers-reduced-motion: reduce)").matches
            ? "instant"
            : "smooth",
        })
      }
    >
      <ArrowDown size={16} /> Latest message
    </button>
  ) : null;
}

export function Message({
  from,
  className = "",
  ...props
}: ComponentProps<"div"> & { from: "user" | "assistant" }) {
  return <div className={`message message-${from} ${className}`} {...props} />;
}

export function MessageActions(props: ComponentProps<"div">) {
  return (
    <div {...props} className={`answer-actions ${props.className || ""}`} />
  );
}
