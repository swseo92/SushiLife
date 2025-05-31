import pstats
import io

def print_profile_stats(profile_filename, num_stats=30):
    """
    Loads a .prof file, sorts by cumulative time, and prints the top N stats.
    """
    print(f"\n--- Stats for {profile_filename} ---")
    s = io.StringIO()
    try:
        ps = pstats.Stats(profile_filename, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(num_stats)
        print(s.getvalue())
    except FileNotFoundError:
        print(f"Error: Profile file '{profile_filename}' not found.")
    except Exception as e:
        print(f"An error occurred while processing '{profile_filename}': {e}")
    finally:
        s.close()

if __name__ == "__main__":
    print_profile_stats("init_profile.prof", 30)
    print_profile_stats("loop_profile.prof", 30)
