// like this 10:34, 12. Juni 2024 but only if the message is older than 1 day, otherwise just show time like 10:34
export const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    const isSameYear = date.getFullYear() === now.getFullYear();

    const options: Intl.DateTimeFormatOptions = isToday
        ? { hour: "2-digit", minute: "2-digit" }
        : isSameYear
        ? { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "short" }
        : { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "short", year: "2-digit" }; 
    return date.toLocaleString(undefined, options);
};