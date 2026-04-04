import ForgeUI, {
  render,
  Fragment,
  IssuePanel,
  Button,
  Text,
  SectionMessage,
  Tag,
  useProductContext,
  useState,
  invoke,
} from "@forge/ui";

// ── Grade colour mapping ──────────────────────────────────────────────────────
const gradeColour = {
  A: "green",
  B: "blue",
  C: "yellow",
  D: "red",
  F: "red",
};

// ── Panel component ───────────────────────────────────────────────────────────
const App = () => {
  const context = useProductContext();
  const issueKey = context.platformContext.issueKey;

  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const handleRunQA = async () => {
    setStatus("loading");
    setResult(null);
    setErrorMsg(null);

    try {
      const response = await invoke("runQA", { issueKey });
      if (response.error) {
        setErrorMsg(response.error);
        setStatus("error");
      } else {
        setResult(response);
        setStatus("done");
      }
    } catch (err) {
      setErrorMsg(err.message || "Unexpected error — check platform logs.");
      setStatus("error");
    }
  };

  return (
    <Fragment>
      {status === "idle" && (
        <Fragment>
          <Text>
            Run an AI-powered QA analysis on this ticket. The result will be
            posted as a Jira comment and shown here.
          </Text>
          <Button
            text="Run QA AI Analysis"
            onClick={handleRunQA}
            appearance="primary"
          />
        </Fragment>
      )}

      {status === "loading" && (
        <SectionMessage appearance="information" title="Analysis in progress…">
          <Text>
            The QA Agent is analysing {issueKey}. This takes ~60–90 seconds.
            A comment will be posted to this ticket when complete.
          </Text>
        </SectionMessage>
      )}

      {status === "done" && result && (
        <Fragment>
          <SectionMessage appearance="confirmation" title="Analysis complete">
            <Text>
              Score: {result.quality_score ?? "n/a"}/100 &nbsp;
              Grade: <Tag text={result.grade ?? "n/a"} color={gradeColour[result.grade] ?? "grey"} />
            </Text>
            {result.summary && <Text>{result.summary}</Text>}
          </SectionMessage>
          <Button
            text="Run Again"
            onClick={handleRunQA}
            appearance="subtle"
          />
        </Fragment>
      )}

      {status === "error" && (
        <Fragment>
          <SectionMessage appearance="error" title="Analysis failed">
            <Text>{errorMsg}</Text>
          </SectionMessage>
          <Button
            text="Retry"
            onClick={handleRunQA}
            appearance="subtle"
          />
        </Fragment>
      )}
    </Fragment>
  );
};

export const run = render(
  <IssuePanel>
    <App />
  </IssuePanel>
);
