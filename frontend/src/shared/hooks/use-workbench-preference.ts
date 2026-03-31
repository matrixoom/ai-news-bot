import { useEffect, useState } from "react";
import {
  readBooleanPreference,
  readStringPreference,
  subscribeToPreference,
  writePreference,
} from "../lib/workbench-preferences";

export function useStringWorkbenchPreference(key: string, fallback: string) {
  const [value, setValue] = useState(() => readStringPreference(key, fallback));

  useEffect(() => subscribeToPreference(key, setValue), [key]);

  return {
    value,
    setValue: (nextValue: string) => {
      setValue(nextValue);
      writePreference(key, nextValue);
    },
  };
}

export function useBooleanWorkbenchPreference(key: string, fallback: boolean) {
  const [value, setValue] = useState(() => readBooleanPreference(key, fallback));

  useEffect(
    () =>
      subscribeToPreference(key, (nextValue) => {
        setValue(nextValue === "true");
      }),
    [key],
  );

  return {
    value,
    setValue: (nextValue: boolean) => {
      setValue(nextValue);
      writePreference(key, nextValue);
    },
  };
}
