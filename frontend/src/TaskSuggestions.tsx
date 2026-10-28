import { useEffect, useMemo, useRef, useState } from "react";
import {
  autoUpdate,
  flip,
  FloatingFocusManager,
  offset,
  safePolygon,
  shift,
  size,
  useClick,
  useDismiss,
  useFloating,
  useFocus,
  useHover,
  useInteractions,
  useListNavigation,
  useRole,
  useTypeahead,
} from "@floating-ui/react";
import {
  BarChart3,
  Check,
  ChevronRight,
  Search,
  SlidersHorizontal,
  TrendingUp,
} from "lucide-react";
import type { Dataset } from "./types";
import {
  buildTaskSuggestions,
  type TaskId,
  type SuggestionGroup,
} from "./suggestionBuilder";

const tasks = [
  {
    id: "explore",
    label: "Explore my data",
    icon: Search,
    prompt: "Summarize the key patterns in this dataset.",
  },
  {
    id: "chart",
    label: "Create a chart",
    icon: BarChart3,
    prompt: "Create a chart showing ",
  },
  {
    id: "compare",
    label: "Compare groups",
    icon: SlidersHorizontal,
    prompt: "Compare ",
  },
  {
    id: "trends",
    label: "Find trends",
    icon: TrendingUp,
    prompt: "What trends are present in this dataset?",
  },
  {
    id: "quality",
    label: "Check data quality",
    icon: Check,
    prompt: "Check for missing values, duplicates and data quality issues.",
  },
] as const;
type Task = (typeof tasks)[number];

function TaskMenu({
  task,
  group,
  open,
  changeOpen,
  disabled,
  choose,
}: {
  task: Task;
  group: SuggestionGroup;
  open: boolean;
  changeOpen: (open: boolean) => void;
  disabled: boolean;
  choose: (value: string) => void;
}) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const listRef = useRef<(HTMLButtonElement | null)[]>([]);
  const labels = useRef<(string | null)[]>([]);
  labels.current = group.items.map((item) => item.label);
  const { refs, floatingStyles, context } = useFloating({
    open: open && !disabled,
    onOpenChange: changeOpen,
    placement: "top-start",
    strategy: "fixed",
    whileElementsMounted: autoUpdate,
    middleware: [
      offset(10),
      flip({ padding: 12 }),
      shift({ padding: 12 }),
      size({
        padding: 12,
        apply({ availableHeight, elements }) {
          elements.floating.style.maxHeight = `${Math.max(0, Math.min(440, availableHeight))}px`;
        },
      }),
    ],
  });
  const hover = useHover(context, {
    enabled: !disabled,
    mouseOnly: true,
    delay: { open: 140, close: 180 },
    handleClose: safePolygon({ blockPointerEvents: false }),
  });
  const focus = useFocus(context, { enabled: !disabled });
  const click = useClick(context, { enabled: !disabled });
  const dismiss = useDismiss(context);
  const role = useRole(context, { role: "menu" });
  const navigation = useListNavigation(context, {
    listRef,
    activeIndex,
    onNavigate: setActiveIndex,
    loop: true,
  });
  const typeahead = useTypeahead(context, {
    listRef: labels,
    activeIndex,
    onMatch: setActiveIndex,
  });
  const { getReferenceProps, getFloatingProps, getItemProps } = useInteractions(
    [hover, focus, click, dismiss, role, navigation, typeahead],
  );
  useEffect(() => {
    if (!open) setActiveIndex(null);
  }, [open]);
  return (
    <>
      <button
        className="task-trigger"
        ref={refs.setReference}
        disabled={disabled}
        {...getReferenceProps()}
      >
        <task.icon size={15} />
        {task.label}
      </button>
      {open && !disabled ? (
        <FloatingFocusManager
          context={context}
          modal={false}
          initialFocus={-1}
          guards={false}
        >
          <div
            ref={refs.setFloating}
            style={floatingStyles}
            className="task-menu"
            {...getFloatingProps({
              "aria-label": `${task.label} suggestions`,
            })}
          >
            <div className="task-menu-heading" role="presentation">
              <strong>{task.label}</strong>
              <span>
                {group.limited
                  ? "Top 10 suggestions"
                  : "Choose a question to edit"}
              </span>
            </div>
            {group.items.length ? (
              group.items.map((item, index) => (
                <button
                  key={item.prompt}
                  ref={(element) => {
                    listRef.current[index] = element;
                  }}
                  role="menuitem"
                  tabIndex={activeIndex === index ? 0 : -1}
                  className="task-option"
                  {...getItemProps({
                    onClick() {
                      changeOpen(false);
                      requestAnimationFrame(() => choose(item.prompt));
                    },
                  })}
                >
                  <span>{item.label}</span>
                  <ChevronRight size={14} />
                </button>
              ))
            ) : (
              <p className="task-menu-empty" role="presentation">
                {group.empty}
              </p>
            )}
            <p className="task-menu-foot" role="presentation">
              You can also type your own question.
            </p>
          </div>
        </FloatingFocusManager>
      ) : null}
    </>
  );
}

export default function TaskSuggestions({
  dataset,
  disabled,
  onChoose,
  hasResult = false,
}: {
  dataset: Dataset | null | undefined;
  disabled: boolean;
  onChoose: (value: string) => void;
  hasResult?: boolean;
}) {
  const [openTask, setOpenTask] = useState<TaskId | null>(null);
  const groups = useMemo(() => {
    if (!dataset) return null;
    const result = buildTaskSuggestions(dataset);
    if (hasResult) {
      const items = [
        {
          label: "Chart the previous result",
          prompt: "Create a chart of the previous result.",
        },
        ...result.chart.items,
      ];
      result.chart = {
        ...result.chart,
        items: items.slice(0, 10),
        limited: result.chart.limited || items.length > 10,
      };
    }
    return result;
  }, [dataset, hasResult]);
  useEffect(() => {
    setOpenTask(null);
  }, [dataset, disabled]);
  return (
    <div className="task-buttons" role="group" aria-label="Suggested tasks">
      {tasks.map((task) =>
        groups ? (
          <TaskMenu
            key={task.id}
            task={task}
            group={groups[task.id]}
            disabled={disabled}
            open={openTask === task.id}
            changeOpen={(open) =>
              setOpenTask((current) =>
                open ? task.id : current === task.id ? null : current,
              )
            }
            choose={onChoose}
          />
        ) : (
          <button
            key={task.id}
            disabled={disabled}
            onClick={() => onChoose(task.prompt)}
          >
            <task.icon size={15} />
            {task.label}
          </button>
        ),
      )}
    </div>
  );
}
