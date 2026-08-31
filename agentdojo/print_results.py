import argparse, json, glob, os

parser = argparse.ArgumentParser()
parser.add_argument("--model", default="Qwen3.6-35B-A3B")
parser.add_argument("--log-dir", default="logs")
parser.add_argument("--attack", default="important_instructions")
args = parser.parse_args()

log_dir = args.log_dir
# Logs are stored under <model>+progent when Progent is enabled (the default).
model = args.model.split("/")[-1]
if os.getenv("SECAGENT_GENERATE", "True").lower() == "true":
    model += "+progent"
attack = args.attack

results = {}
for suite in ["banking", "slack", "travel", "workspace"]:
    # if attack is None:
    pattern = f"{log_dir}/{model}/{suite}/user_task_*/none/none.json"
    # else:
    #     pattern = f"{log_dir}/{model}/{suite}/user_task_*/{attack}/injection_task_*.json"

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

print(f"\n{'Suite':<12} {'Utility':>8} {'Security':>10}")
print("-" * 32)
for suite, scores in results.items():
    print(f"{suite:<12} {str(scores['utility'])[:6]:>8} {str(scores['security'])[:6]:>10}")

u = [v["utility"] for v in results.values() if isinstance(v["utility"], float)]
s = [v["security"] for v in results.values() if isinstance(v["security"], float)]
print("-" * 32)
if u: print(f"{'avg':<12} {sum(u)/len(u):>8.3f}", end="")
if s: print(f" {sum(s)/len(s):>10.3f}", end="")
print()