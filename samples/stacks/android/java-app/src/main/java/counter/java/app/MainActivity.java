package counter.java.app;

import android.app.Activity;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import counter.java.CounterViewModel;

/** Java Android screen over the Java Core. The views hold no state of their own. */
public final class MainActivity extends Activity {
    private final CounterViewModel vm = new CounterViewModel();
    private TextView label;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        label = new TextView(this);
        label.setTextSize(48f);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.addView(label);
        layout.addView(button("−", new CounterViewModel.Decrement()));
        layout.addView(button("+", new CounterViewModel.Increment()));
        layout.addView(button("Reset", new CounterViewModel.Reset()));
        setContentView(layout);
        render();
    }

    private Button button(String title, CounterViewModel.Action action) {
        Button button = new Button(this);
        button.setText(title);
        button.setOnClickListener(view -> { vm.send(action); render(); });
        return button;
    }

    private void render() { label.setText(String.valueOf(vm.getState().count)); }
}
