using AISecutity.Models;

namespace AISecutity
{
    public class ActivityManager
    {
        private readonly List<ActivityEvent> _activities;
        public ActivityManager()
        {
            _activities = new List<ActivityEvent>();
        }
        public void AddActivity(ActivityEvent activity)
        {
            _activities.Add(activity);
        }
        public IEnumerable<ActivityEvent> GetActivities()
        {
            return _activities;
        }
    }
}
