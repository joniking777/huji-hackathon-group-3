namespace AISecutity
{
    public class ActivityManager
    {
        private readonly List<Activity> _activities;
        public ActivityManager()
        {
            _activities = new List<Activity>();
        }
        public void AddActivity(Activity activity)
        {
            _activities.Add(activity);
        }
        public IEnumerable<Activity> GetActivities()
        {
            return _activities;
        }
    }
}
