from analysis import run_analysis
from reporting import build_reports
from sqlite_verify import load_clean_events, run_verification
from visualize import generate_charts


def main() -> None:
    print("1/4 pandas analysis", flush=True)
    run_analysis()
    print("2/4 sqlite verification", flush=True)
    load_clean_events()
    checks = run_verification()
    print(checks, flush=True)
    print("3/4 charts", flush=True)
    generate_charts()
    print("4/4 reports", flush=True)
    build_reports()
    print("pipeline complete", flush=True)


if __name__ == "__main__":
    main()
