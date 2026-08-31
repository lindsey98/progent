import argparse
import glob
import json

SUITES = ["shopping", "github", "dailylife", "banking", "slack", "travel", "workspace"]


def run_dir_name(model: str, defense: str | None) -> str:
    """Mirror AgentDyn's pipeline naming: `<model>-<defense>` when a defense is used."""
    name = model.split("/")[-1]
    if defense:
        name += f"-{defense}"
    return name


def summarize(log_dir: str, name: str, attack):
    results = {}
    for suite in SUITES:
        if attack is None:
            pattern = f"{log_dir}/{name}/{suite}/user_task_*/none/none.json"
        else:
            pattern = f"{log_dir}/{name}/{suite}/user_task_*/{attack}/injection_task_*.json"
        files = glob.glob(pattern)
        if not files:
            continue
        utility_scores, security_scores = [], []
        for f in files:
            with open(f) as fp:
                data = json.load(fp)
            if "utility" in data:
                utility_scores.append(data["utility"])
            if "security" in data:
                security_scores.append(data["security"])
        results[suite] = {
            "utility": sum(utility_scores) / len(utility_scores) if utility_scores else "N/A",
            "security": sum(security_scores) / len(security_scores) if security_scores else "N/A",
        }
    return results


def print_table(title: str, results: dict):
    print(f"\n=== {title} ===")
    if not results:
        print("(no logs found)")
        return
    print(f"{'Suite':<12} {'Utility':>8} {'Security':>10}")
    print("-" * 32)
    for suite, scores in results.items():
        print(f"{suite:<12} {str(scores['utility'])[:6]:>8} {str(scores['security'])[:6]:>10}")
    u = [v["utility"] for v in results.values() if isinstance(v["utility"], float)]
    s = [v["security"] for v in results.values() if isinstance(v["security"], float)]
    print("-" * 32)
    line = f"{'avg':<12}"
    if u:
        line += f" {sum(u) / len(u):>8.3f}"
    if s:
        line += f" {sum(s) / len(s):>10.3f}"
    print(line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize AgentDyn results (utility/security per suite).")
    parser.add_argument("--model", default="Qwen3.6-35B-A3B",
                        help="Model id; the -<defense> suffix is applied automatically.")
    parser.add_argument("--defense", default="progent",
                        help="Defense used for the run (part of the run-directory name).")
    parser.add_argument("--name", default=None,
                        help="Exact run-directory name under --log-dir (overrides --model/--defense).")
    parser.add_argument("--log-dir", default="logs")
    args = parser.parse_args()

    name = args.name or run_dir_name(args.model, args.defense)
    print(f"Results for: {name}")
    for attack, title in [(None, "No attack"), ("important_instructions", "Attack: important_instructions")]:
        print_table(title, summarize(args.log_dir, name, attack))
