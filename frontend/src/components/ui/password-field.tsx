import { forwardRef, useState, type ComponentProps } from "react";
import { TextField } from "@/components/ui/text-field";
import { Button } from "@/components/ui/button";

type PasswordFieldProps = Omit<
  ComponentProps<typeof TextField>,
  "type" | "trailing"
>;

export const PasswordField = forwardRef<HTMLInputElement, PasswordFieldProps>(
  function PasswordField(props, ref) {
    const [visible, setVisible] = useState(false);

    return (
      <TextField
        {...props}
        ref={ref}
        type={visible ? "text" : "password"}
        autoComplete={props.autoComplete ?? "current-password"}
        trailing={
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label={visible ? "Hide password" : "Show password"}
            onClick={() => setVisible((v) => !v)}
          >
            <span className="text-[11px] font-semibold text-text-faint">
              {visible ? "Hide" : "Show"}
            </span>
          </Button>
        }
      />
    );
  },
);
