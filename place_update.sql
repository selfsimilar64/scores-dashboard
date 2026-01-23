UPDATE scores
SET Place = (
    SELECT s.Place
    FROM csv_staging AS s
    WHERE s.AthleteName = scores.AthleteName AND
    s.Level = scores.Level AND
    s.CompYear = scores.CompYear AND
    s.MeetName = scores.MeetName AND
    s.CompYear <= 2024 AND
    s.Event = scores.Event
)
WHERE EXISTS (
    SELECT 1
    FROM csv_staging AS s
    WHERE s.AthleteName = scores.AthleteName AND
    s.Level = scores.Level AND
    s.CompYear = scores.CompYear AND
    s.MeetName = scores.MeetName AND
    s.CompYear <= 2024 AND
    s.Event = scores.Event
);