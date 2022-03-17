import sagecell from "./sagecell";

export const origConsole = window.console;

/**
 * A replacement for window.console that suppresses logging based on `sagecell.quietMode`
 */
export const console = {
    log(...args) {
        if (sagecell.quietMode) {
            return;
        }
        origConsole.log(...args);
    },
    info(...args) {
        if (sagecell.quietMode) {
            return;
        }
        origConsole.info(...args);
    },
    debug(...args) {
        if (sagecell.quietMode) {
            return;
        }
        origConsole.debug(...args);
    },
    error(...args) {
        origConsole.error(...args);
    },
    warn(...args) {
        origConsole.warn(...args);
    },
};
