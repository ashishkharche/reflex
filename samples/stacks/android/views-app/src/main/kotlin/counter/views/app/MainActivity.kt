package counter.views.app

import android.app.Activity
import android.os.Bundle
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import counter.views.CounterViewModel
import counter.views.CounterViewModel.Action

/** Android Views screen over the shared Core. The views hold no state of their own. */
class MainActivity : Activity() {
    private val vm = CounterViewModel()
    private lateinit var label: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        label = TextView(this).apply { textSize = 48f }
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        layout.addView(label)
        layout.addView(button("−") { vm.send(Action.Decrement) })
        layout.addView(button("+") { vm.send(Action.Increment) })
        layout.addView(button("Reset") { vm.send(Action.Reset) })
        setContentView(layout)
        render()
    }

    private fun button(title: String, action: () -> Unit) = Button(this).apply {
        text = title
        setOnClickListener { action(); render() }
    }

    private fun render() { label.text = vm.state.count.toString() }
}
